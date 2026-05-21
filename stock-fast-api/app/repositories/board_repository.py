import re
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.exceptions import NotFoundException
from app.utils.pagination import paginate
from app.utils.validation import validate_sort_field, validate_sort_order


class BoardRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_boards(
        self,
        board_type: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        """
        从 dwd_board_master 查询板块列表。
        支持 board_type 过滤和板块名称关键字搜索。
        同时返回各板块的成分股数量（来自 dwd_board_relation）。
        """
        sql = """
            SELECT b.board_code, b.board_name, b.board_type,
                   b.parent_board_code, b.is_active,
                   COUNT(r.symbol) AS member_count
            FROM dwd_board_master b
            LEFT JOIN dwd_board_relation r
                ON b.board_code = r.board_code
            WHERE b.is_active = true
        """
        params: dict = {}
        if board_type:
            sql += " AND b.board_type = :board_type"
            params["board_type"] = board_type.upper()
        if keyword:
            sql += " AND b.board_name LIKE :keyword"
            params["keyword"] = f"%{keyword}%"

        sql += " GROUP BY b.board_code, b.board_name, b.board_type, b.parent_board_code, b.is_active"
        sql += " ORDER BY b.board_code"

        result = self.db.execute(text(sql), params)
        rows = result.fetchall()

        items = [
            {
                "board_code": row._mapping["board_code"],
                "board_name": row._mapping["board_name"],
                "board_type": row._mapping["board_type"],
                "parent_board_code": row._mapping["parent_board_code"],
                "is_active": bool(row._mapping["is_active"]) if row._mapping["is_active"] is not None else True,
            }
            for row in rows
        ]
        return paginate(items, page, page_size)

    def get_board(self, board_code: str) -> dict | None:
        """根据 board_code 查询板块详情（从 dwd_board_master）"""
        result = self.db.execute(
            text("""
                SELECT board_code, board_name, board_type,
                       parent_board_code, is_active, source
                FROM dwd_board_master
                WHERE board_code = :board_code
            """),
            {"board_code": board_code},
        )
        row = result.fetchone()
        if not row:
            return None

        m = row._mapping
        # 查询成分股数量
        count_result = self.db.execute(
            text("""
                SELECT COUNT(DISTINCT symbol)
                FROM dwd_board_relation
                WHERE board_code = :board_code
            """),
            {"board_code": board_code},
        )
        member_count = count_result.fetchone()[0] or 0

        return {
            "board_code": m["board_code"],
            "board_name": m["board_name"],
            "board_type": m["board_type"],
            "parent_board_code": m["parent_board_code"],
            "is_active": bool(m["is_active"]) if m["is_active"] is not None else True,
        }

    def get_members(
        self,
        board_code: str,
        trade_date: str | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> dict:
        """
        查询板块成分股。

        通过 dwd_board_relation 获取该板块当前所有成分股，
        再 JOIN dwd_stock_daily 获取最新行情（按 trade_date 降序取第一条）。
        支持按 change_pct / turnover_rate_f / market_value / close 排序。
        """
        # 校验排序字段
        allowed_sort = {"change_pct", "turnover_rate_f", "market_value", "close", "symbol"}
        sort_by = validate_sort_field(sort_by, allowed_sort, "sort_by")
        sort_order = validate_sort_order(sort_order)
        sort_dir = "DESC" if sort_order == "desc" else "ASC"

        # 确定排序表达式
        if sort_by == "symbol":
            sort_expr = f"m.ticker {sort_dir}"
        else:
            sort_expr = f"d.{sort_by} {sort_dir} NULLS LAST"

        # 如果没传 trade_date，取最新有数据的交易日
        if not trade_date:
            td_result = self.db.execute(
                text("SELECT MAX(trade_date) FROM dwd_stock_daily")
            )
            trade_date = str(td_result.fetchone()[0] or "")

        # 查询成分股
        sql = text(f"""
            SELECT m.symbol, m.ticker, m.name, m.exchange,
                   m.industry_l1,
                   d.close AS close_price,
                   d.change_pct,
                   d.turnover_rate_f,
                   d.market_value,
                   d.trade_date AS daily_trade_date
            FROM (
                SELECT DISTINCT r.symbol
                FROM dwd_board_relation r
                WHERE r.board_code = :board_code
            ) AS board_members
            JOIN dwd_security_master m ON board_members.symbol = m.symbol
            LEFT JOIN LATERAL (
                SELECT trade_date, close, change_pct, turnover_rate_f, market_value
                FROM dwd_stock_daily
                WHERE symbol = m.symbol
                  AND trade_date <= :trade_date
                ORDER BY trade_date DESC
                LIMIT 1
            ) d ON true
            ORDER BY {sort_expr}
        """)
        result = self.db.execute(sql, {"board_code": board_code, "trade_date": trade_date})
        rows = result.fetchall()

        # 清理 industry_l1 前缀
        def clean_industry(raw: str | None) -> str | None:
            if not raw:
                return None
            return re.sub(r"^[A-Z]\d+", "", raw).lstrip("_ ")

        items = []
        for row in rows:
            m = row._mapping
            items.append({
                "symbol": m["symbol"],
                "name": m["name"],
                "ticker": m["ticker"],
                "exchange": m["exchange"],
                "industry_l1": clean_industry(m["industry_l1"]),
                "close": float(m["close_price"]) if m["close_price"] is not None else None,
                "change_pct": float(m["change_pct"]) if m["change_pct"] is not None else None,
                "turnover_rate": float(m["turnover_rate_f"]) if m["turnover_rate_f"] is not None else None,
                "market_value": float(m["market_value"]) if m["market_value"] is not None else None,
            })

        return paginate(items, page, page_size)
