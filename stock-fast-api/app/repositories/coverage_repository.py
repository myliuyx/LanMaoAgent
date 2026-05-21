import re
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.exceptions import ValidationException
from app.utils.pagination import paginate
from app.utils.safe_float import _clean_industry


class CoverageRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_summary(self) -> dict:
        """
        数据覆盖摘要（对齐 /coverage/summary 接口）。

        字段与 Registry 一致：
        - total_symbols: 上市股票总数
        - daily_fully_covered_symbols: 最新交易日有日线数据的股票数
        - financial_fully_covered_symbols: 有财务数据的股票数
        - adjust_factor_fully_covered_symbols: 有复权因子数据的股票数（dwd_stock_adjust_factor）
        - latest_daily_trade_date: 最新日线数据日期
        - latest_financial_report_period: 最新财务报告期
        """
        # 上市股票总数
        r = self.db.execute(text("""
            SELECT COUNT(*) FROM dwd_security_master WHERE status = 'LISTED'
        """))
        total_symbols = r.fetchone()[0] or 0

        # 最新交易日有日线数据的股票数
        r = self.db.execute(text("""
            SELECT COUNT(DISTINCT symbol)
            FROM dwd_stock_daily
            WHERE trade_date = (SELECT MAX(trade_date) FROM dwd_stock_daily)
        """))
        daily_fully_covered = r.fetchone()[0] or 0

        # 有财务数据的股票数
        r = self.db.execute(text("""
            SELECT COUNT(DISTINCT symbol)
            FROM dwd_stock_financial_indicator
        """))
        financial_fully_covered = r.fetchone()[0] or 0

        # 有复权因子数据的股票数
        r = self.db.execute(text("""
            SELECT COUNT(DISTINCT symbol)
            FROM dwd_stock_adjust_factor
        """))
        adjust_factor_fully_covered = r.fetchone()[0] or 0

        # 最新日线数据日期
        r = self.db.execute(text("SELECT MAX(trade_date) FROM dwd_stock_daily"))
        latest_daily_date = str(r.fetchone()[0] or "")

        # 最新财务报告期
        r = self.db.execute(text("SELECT MAX(report_period) FROM dwd_stock_financial_indicator"))
        latest_finance_date = str(r.fetchone()[0] or "")

        return {
            "total_symbols": total_symbols,
            "daily_fully_covered_symbols": daily_fully_covered,
            "financial_fully_covered_symbols": financial_fully_covered,
            "adjust_factor_fully_covered_symbols": adjust_factor_fully_covered,
            "latest_daily_trade_date": latest_daily_date or None,
            "latest_financial_report_period": latest_finance_date or None,
        }

    def get_list(
        self,
        symbol: str | None,
        data_type: str | None,
        is_full_history: bool | None,
        page: int,
        page_size: int,
    ) -> dict:
        """
        数据覆盖列表（从实际数据表推算，降级实现）。

        由于 etl_data_coverage 为空，按以下规则生成覆盖信息：
        - DAILY: 从 dwd_stock_daily 获取每只股票的首尾日期
        - FINANCE: 从 dwd_stock_financial_indicator 获取首尾日期
        - FACTOR: 从 dwd_stock_factor_daily 获取首尾日期
        """
        # 先用普通字符串构建 SQL，最后再 text()
        params: dict = {}

        if data_type is None or data_type.upper() == "DAILY":
            sql = """
                SELECT m.symbol, m.name,
                       'DAILY' AS data_type,
                       MIN(d.trade_date) AS start_date,
                       MAX(d.trade_date) AS end_date,
                       COUNT(DISTINCT d.trade_date) AS data_days,
                       MAX(d.trade_date) = (SELECT MAX(trade_date) FROM dwd_stock_daily) AS is_latest
                FROM dwd_stock_daily d
                JOIN dwd_security_master m ON d.symbol = m.symbol
                WHERE m.status = 'LISTED'
            """
            if symbol:
                sql += " AND m.symbol = :symbol"
                params["symbol"] = symbol
            sql += " GROUP BY m.symbol, m.name"

        elif data_type.upper() == "FINANCE":
            sql = """
                SELECT m.symbol, m.name,
                       'FINANCE' AS data_type,
                       MIN(f.report_period) AS start_date,
                       MAX(f.report_period) AS end_date,
                       COUNT(*) AS data_days,
                       MAX(f.report_period) >= DATE_TRUNC('quarter', CURRENT_DATE) - INTERVAL '1 day' AS is_latest
                FROM dwd_stock_financial_indicator f
                JOIN dwd_security_master m ON f.symbol = m.symbol
                WHERE m.status = 'LISTED'
            """
            if symbol:
                sql += " AND m.symbol = :symbol"
                params["symbol"] = symbol
            sql += " GROUP BY m.symbol, m.name"

        elif data_type.upper() == "FACTOR":
            sql = """
                SELECT m.symbol, m.name,
                       'FACTOR' AS data_type,
                       MIN(f.trade_date) AS start_date,
                       MAX(f.trade_date) AS end_date,
                       COUNT(*) AS data_days,
                       MAX(f.trade_date) = (SELECT MAX(trade_date) FROM dwd_stock_factor_daily) AS is_latest
                FROM dwd_stock_factor_daily f
                JOIN dwd_security_master m ON f.symbol = m.symbol
                WHERE m.status = 'LISTED'
            """
            if symbol:
                sql += " AND m.symbol = :symbol"
                params["symbol"] = symbol
            sql += " GROUP BY m.symbol, m.name"

        else:
            # 不支持的 data_type，抛出异常
            raise ValidationException(
                code=4005,
                message=f"不支持的 data_type: {data_type}，允许: DAILY, FINANCE, FACTOR",
            )

        result = self.db.execute(text(sql), params)
        rows = result.fetchall()

        items = []
        for row in rows:
            m = row._mapping
            start_date = str(m["start_date"]) if m["start_date"] else None
            end_date = str(m["end_date"]) if m["end_date"] else None

            # 判断是否全量历史：比较 end_date 与该表当前最新日期
            is_full = bool(m["is_latest"]) if m["is_latest"] is not None else False

            if is_full_history is not None:
                if is_full != is_full_history:
                    continue

            items.append({
                "symbol": m["symbol"],
                "name": _clean_industry(m["name"]) or m["symbol"],
                "data_type": m["data_type"],
                "start_date": start_date,
                "end_date": end_date,
                "data_days": m["data_days"],
                "is_full_history": is_full,
                "last_sync_at": end_date + "T23:59:59" if end_date else None,
            })

        return paginate(items, page, page_size)

    def get_detail(self, symbol: str) -> dict:
        """
        单只股票数据覆盖详情（从实际表推算）。
        """
        # 先确认股票存在
        m_result = self.db.execute(
            text("SELECT symbol, name FROM dwd_security_master WHERE symbol = :symbol"),
            {"symbol": symbol},
        )
        m_row = m_result.fetchone()
        if not m_row:
            return {"symbol": symbol, "name": "未知", "coverages": []}

        def clean_industry(raw: str | None) -> str | None:
            if not raw:
                return None
            return re.sub(r"^[A-Z]\d+", "", raw).lstrip("_ ")

        name = _clean_industry(m_row._mapping["name"]) or symbol
        coverages = []

        # 日线覆盖
        r = self.db.execute(
            text("""
                SELECT MIN(trade_date) AS start_date, MAX(trade_date) AS end_date,
                       COUNT(DISTINCT trade_date) AS data_days
                FROM dwd_stock_daily WHERE symbol = :symbol
            """),
            {"symbol": symbol},
        )
        row = r.fetchone()
        if row and row._mapping["start_date"]:
            latest = self.db.execute(text("SELECT MAX(trade_date) FROM dwd_stock_daily")).fetchone()[0]
            coverages.append({
                "data_type": "DAILY",
                "start_date": str(row._mapping["start_date"]),
                "end_date": str(row._mapping["end_date"]),
                "data_days": row._mapping["data_days"],
                "is_full_history": str(row._mapping["end_date"]) == str(latest),
                "last_sync_at": str(row._mapping["end_date"]) + "T23:59:59",
            })

        # 财务覆盖
        r = self.db.execute(
            text("""
                SELECT MIN(report_period) AS start_date, MAX(report_period) AS end_date,
                       COUNT(*) AS data_days
                FROM dwd_stock_financial_indicator WHERE symbol = :symbol
            """),
            {"symbol": symbol},
        )
        row = r.fetchone()
        if row and row._mapping["start_date"]:
            coverages.append({
                "data_type": "FINANCE",
                "start_date": str(row._mapping["start_date"]),
                "end_date": str(row._mapping["end_date"]),
                "data_days": row._mapping["data_days"],
                "is_full_history": True,  # 财务数据发布后不新增，历史固定
                "last_sync_at": str(row._mapping["end_date"]) + "T23:59:59",
            })

        # 因子覆盖
        r = self.db.execute(
            text("""
                SELECT MIN(trade_date) AS start_date, MAX(trade_date) AS end_date,
                       COUNT(*) AS data_days
                FROM dwd_stock_factor_daily WHERE symbol = :symbol
            """),
            {"symbol": symbol},
        )
        row = r.fetchone()
        if row and row._mapping["start_date"]:
            latest = self.db.execute(text("SELECT MAX(trade_date) FROM dwd_stock_factor_daily")).fetchone()[0]
            coverages.append({
                "data_type": "FACTOR",
                "start_date": str(row._mapping["start_date"]),
                "end_date": str(row._mapping["end_date"]),
                "data_days": row._mapping["data_days"],
                "is_full_history": str(row._mapping["end_date"]) == str(latest),
                "last_sync_at": str(row._mapping["end_date"]) + "T23:59:59",
            })

        return {
            "symbol": symbol,
            "name": name,
            "coverages": coverages,
        }
