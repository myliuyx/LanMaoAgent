import re
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.exceptions import NotFoundException
from app.schemas.selection import (
    SelectionFilters,
    SelectionQueryRequest,
    SelectionItem,
)
from app.utils.safe_float import _safe_float, _clean_industry


class SelectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def query_selection(self, req: SelectionQueryRequest) -> dict:
        """
        查询选股结果。
        mart_stock_selection_daily 表按 trade_date + symbol 存储每日选股宽表，
        由 ETL 任务每日收盘后生成。
        """
        # 基础 SQL
        base_sql = """
            FROM mart_stock_selection_daily s
            JOIN dwd_security_master m ON s.symbol = m.symbol
            WHERE s.trade_date = :trade_date
        """
        params = {"trade_date": req.trade_date}

        # --- 筛选条件动态拼装 ---
        # 关键词（名字或代码模糊匹配）
        if req.filters.keyword:
            base_sql += " AND (m.name LIKE :kw OR m.ticker LIKE :kw)"
            params["kw"] = f"%{req.filters.keyword}%"

        # 交易所
        if req.filters.exchange:
            base_sql += " AND m.exchange = :exchange"
            params["exchange"] = req.filters.exchange

        # ST 状态
        if req.filters.is_st is not None:
            base_sql += " AND m.is_st = :is_st"
            params["is_st"] = req.filters.is_st

        # 行业（支持模糊匹配，去掉前缀后比较）
        if req.filters.industry_l1:
            base_sql += " AND m.industry_l1 LIKE :industry_pattern"
            params["industry_pattern"] = f"%{req.filters.industry_l1}%"

        # 市值区间
        if req.filters.market_value_min is not None:
            base_sql += " AND s.market_value >= :market_value_min"
            params["market_value_min"] = req.filters.market_value_min
        if req.filters.market_value_max is not None:
            base_sql += " AND s.market_value <= :market_value_max"
            params["market_value_max"] = req.filters.market_value_max

        # 换手率区间
        if req.filters.turnover_rate_min is not None:
            base_sql += " AND s.turnover_rate_f >= :turnover_rate_min"
            params["turnover_rate_min"] = req.filters.turnover_rate_min
        if req.filters.turnover_rate_max is not None:
            base_sql += " AND s.turnover_rate_f <= :turnover_rate_max"
            params["turnover_rate_max"] = req.filters.turnover_rate_max

        # ROE
        if req.filters.roe_min is not None:
            base_sql += " AND s.roe >= :roe_min"
            params["roe_min"] = req.filters.roe_min

        # 营收增速
        if req.filters.revenue_yoy_min is not None:
            base_sql += " AND s.revenue_yoy >= :revenue_yoy_min"
            params["revenue_yoy_min"] = req.filters.revenue_yoy_min

        # 净利润增速
        if req.filters.net_profit_yoy_min is not None:
            base_sql += " AND s.net_profit_yoy >= :net_profit_yoy_min"
            params["net_profit_yoy_min"] = req.filters.net_profit_yoy_min

        # 是否突破 60日新高
        if req.filters.is_new_high_60d is not None:
            base_sql += " AND s.is_new_high_60d = :is_new_high_60d"
            params["is_new_high_60d"] = req.filters.is_new_high_60d

        # 是否突破 MA20
        if req.filters.is_break_ma20 is not None:
            base_sql += " AND s.is_break_ma20 = :is_break_ma20"
            params["is_break_ma20"] = req.filters.is_break_ma20

        # 趋势评分
        if req.filters.trend_score_min is not None:
            base_sql += " AND s.trend_score >= :trend_score_min"
            params["trend_score_min"] = req.filters.trend_score_min

        # --- 排序（白名单校验，防止注入） ---
        ALLOWED_SORT_COLS = {
            "trend_score": "s.trend_score",
            "roe": "s.roe",
            "revenue_yoy": "s.revenue_yoy",
            "net_profit_yoy": "s.net_profit_yoy",
            "market_value": "s.market_value",
            "change_pct": "s.change_pct",
            "turnover_rate": "s.turnover_rate_f",
        }
        sort_col = req.sort_by or "trend_score"
        sort_col_sql = ALLOWED_SORT_COLS.get(sort_col, "s.trend_score")
        sort_dir = "DESC" if req.sort_order == "desc" else "ASC"
        order_sql = f" ORDER BY {sort_col_sql} {sort_dir}"

        # --- 计算总数 ---
        count_sql = f"SELECT COUNT(*) {base_sql}"
        total = self.db.execute(text(count_sql), params).fetchone()[0]

        # --- 分页查询数据 ---
        offset = (req.page - 1) * req.page_size
        params["limit"] = req.page_size
        params["offset"] = offset

        select_sql = f"""
            SELECT s.symbol, m.name AS name, m.exchange,
                   NULLIF(m.industry_l1, '') AS industry_l1,
                   s.is_st,
                   s.close_price, s.change_pct, s.turnover_rate_f,
                   s.market_value,
                   s.ma20, s.ma60,
                   s.is_new_high_60d, s.is_break_ma20,
                   s.roe, s.revenue_yoy, s.net_profit_yoy, s.trend_score,
                   s.composite_score, s.rank_pct
            {base_sql}
            {order_sql}
            LIMIT :limit OFFSET :offset
        """
        result = self.db.execute(text(select_sql), params)
        rows = result.fetchall()

        # 清理 industry_l1 的分类前缀（如 "C15酒、饮料..." → "酒、饮料..."）
        items = [
            {
                "symbol": row._mapping["symbol"],
                "name": row._mapping["name"],
                "exchange": row._mapping["exchange"],
                "industry_l1": _clean_industry(row._mapping["industry_l1"]),
                "is_st": bool(row._mapping["is_st"]) if row._mapping["is_st"] is not None else False,
                "close": _safe_float(row._mapping["close_price"]),
                "change_pct": _safe_float(row._mapping["change_pct"]),
                "turnover_rate": _safe_float(row._mapping["turnover_rate_f"]),
                "market_value": _safe_float(row._mapping["market_value"]),
                "ma20": _safe_float(row._mapping["ma20"]),
                "ma60": _safe_float(row._mapping["ma60"]),
                "is_new_high_60d": bool(row._mapping["is_new_high_60d"]) if row._mapping["is_new_high_60d"] is not None else False,
                "is_break_ma20": bool(row._mapping["is_break_ma20"]) if row._mapping["is_break_ma20"] is not None else False,
                "roe": _safe_float(row._mapping["roe"]),
                "revenue_yoy": _safe_float(row._mapping["revenue_yoy"]),
                "net_profit_yoy": _safe_float(row._mapping["net_profit_yoy"]),
                "trend_score": _safe_float(row._mapping["trend_score"]),
            }
            for row in rows
        ]

        return {
            "list": items,
            "page": req.page,
            "page_size": req.page_size,
            "total": total,
        }

    def get_dates(
        self, start_date: str | None, end_date: str | None, limit: int
    ) -> list[str]:
        """
        返回有实际选股数据的交易日列表（降序）。
        - 优先从 mart_stock_selection_daily 取有数据的日期
        - 如果该表为空（ETL未运行），则回退到 dwd_stock_factor_daily（因子数据截止日 2026-04-24）
        - 不返回未来日期，避免用户选了没数据的日期
        """
        # 先尝试从 mart_stock_selection_daily 取有数据的日期
        sql = text("""
            SELECT DISTINCT trade_date
            FROM mart_stock_selection_daily
            WHERE trade_date <= CURRENT_DATE
        """)
        result = self.db.execute(sql)
        rows = result.fetchall()

        if rows:
            dates = sorted([str(row[0]) for row in rows], reverse=True)
            # 应用 limit
            return dates[:limit]

        # 回退：mart_stock_selection_daily 为空，则从 dwd_stock_factor_daily 取最新有因子数据的日期
        sql_fallback = text("""
            SELECT DISTINCT trade_date
            FROM dwd_stock_factor_daily
            WHERE trade_date <= CURRENT_DATE
            ORDER BY trade_date DESC
            LIMIT :limit
        """)
        result_fallback = self.db.execute(sql_fallback, {"limit": limit})
        return [str(row[0]) for row in result_fallback.fetchall()]

    def get_industries(self) -> list[str]:
        """
        从 dwd_security_master 抽取唯一行业分类（industry_l1）列表。
        - 去重在清理前缀之前进行（按原始值去重）
        - 返回可读行业名称（去掉字母数字混合前缀）
        - 按清理后名称排序
        """
        result = self.db.execute(
            text("""
                SELECT DISTINCT industry_l1
                FROM dwd_security_master
                WHERE industry_l1 IS NOT NULL AND industry_l1 != ''
            """)
        )
        rows = result.fetchall()

        # 先去重（按原始值），再清理前缀，避免 'C15酒...' 和 'C15酒、...' 被当作不同记录
        seen_raw: set[str] = set()
        cleaned_map: dict[str, str] = {}  # raw -> cleaned

        for row in rows:
            raw = row._mapping["industry_l1"]
            if not raw or raw in seen_raw:
                continue
            seen_raw.add(raw)
            cleaned = re.sub(r"^[A-Z]\d+", "", raw).lstrip("_ ")
            if cleaned:
                cleaned_map[raw] = cleaned

        # 按清理后名称排序返回
        return sorted(cleaned_map.values())

    def get_selection_top(self, days: int, limit: int) -> list[dict]:
        """
        获取选股结果Top榜。

        按 symbol 分组聚合近 N 个交易日（由 days 参数指定）的选股记录。
        排序规则：按 selection_count 降序，再按 avg_trend_score 降序。

        数据来源：mart_stock_selection_daily
        """
        # 获取近 N 个交易日的最大日期
        result = self.db.execute(
            text("""
                SELECT MAX(trade_date) as max_date
                FROM mart_stock_selection_daily
                WHERE trade_date <= CURRENT_DATE
            """)
        )
        max_date = result.fetchone()[0]
        if not max_date:
            return []

        # 计算起始日期（往回数个交易日）
        result = self.db.execute(
            text("""
                SELECT trade_date
                FROM (
                    SELECT DISTINCT trade_date,
                           ROW_NUMBER() OVER (ORDER BY trade_date DESC) as rn
                    FROM mart_stock_selection_daily
                    WHERE trade_date <= CURRENT_DATE
                ) sub
                WHERE rn = :days
            """),
            {"days": days}
        )
        row = result.fetchone()
        start_date = row[0] if row else None
        if not start_date:
            # 如果不足 days 天，则取最早日期
            result = self.db.execute(
                text("SELECT MIN(trade_date) FROM mart_stock_selection_daily")
            )
            start_date = result.fetchone()[0]

        # 聚合查询：按 symbol 分组，计算各项指标
        result = self.db.execute(
            text(f"""
                WITH recent AS (
                    -- 近 N 日选股记录
                    SELECT symbol, name, exchange, industry_l1,
                           close_price, change_pct, turnover_rate_f,
                           is_new_high_60d, is_break_ma20,
                           trend_score, roe, revenue_yoy, net_profit_yoy,
                           trade_date,
                           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) as latest_rn
                    FROM mart_stock_selection_daily
                    WHERE trade_date >= :start_date AND trade_date <= :end_date
                ),
                aggregated AS (
                    SELECT
                        symbol,
                        MAX(name) as name,
                        MAX(exchange) as exchange,
                        MAX(industry_l1) as industry_l1_raw,
                        COUNT(*) as selection_count,
                        AVG(trend_score) as avg_trend_score,
                        AVG(roe) as avg_roe,
                        AVG(revenue_yoy) as avg_revenue_yoy,
                        AVG(net_profit_yoy) as avg_net_profit_yoy,
                        SUM(CASE WHEN is_new_high_60d = true THEN 1 ELSE 0 END) as high_60d_count,
                        SUM(CASE WHEN is_break_ma20 = true THEN 1 ELSE 0 END) as break_ma20_count,
                        MAX(trade_date) as latest_date
                    FROM recent
                    GROUP BY symbol
                )
                SELECT
                    a.symbol,
                    a.name,
                    a.exchange,
                    a.industry_l1_raw,
                    a.selection_count,
                    a.avg_trend_score,
                    a.avg_roe,
                    a.avg_revenue_yoy,
                    a.avg_net_profit_yoy,
                    a.high_60d_count,
                    a.break_ma20_count,
                    a.latest_date,
                    r.close_price,
                    r.change_pct,
                    r.turnover_rate_f,
                    r.is_new_high_60d,
                    r.is_break_ma20
                FROM aggregated a
                JOIN recent r ON a.symbol = r.symbol AND r.latest_rn = 1
                ORDER BY a.selection_count DESC, a.avg_trend_score DESC NULLS LAST
                LIMIT :limit
            """),
            {"start_date": start_date, "end_date": max_date, "limit": limit}
        )

        items = []
        for row in result:
            m = row._mapping
            items.append({
                "symbol": m["symbol"],
                "name": m["name"],
                "exchange": m["exchange"],
                "industry_l1": _clean_industry(m["industry_l1_raw"]),
                "selection_count": m["selection_count"],
                "avg_trend_score": _safe_float(m["avg_trend_score"]),
                "avg_roe": _safe_float(m["avg_roe"]),
                "avg_revenue_yoy": _safe_float(m["avg_revenue_yoy"]),
                "avg_net_profit_yoy": _safe_float(m["avg_net_profit_yoy"]),
                "high_60d_count": m["high_60d_count"],
                "break_ma20_count": m["break_ma20_count"],
                "latest_date": str(m["latest_date"]) if m["latest_date"] else None,
                "close": _safe_float(m["close_price"]),
                "change_pct": _safe_float(m["change_pct"]),
                "turnover_rate": _safe_float(m["turnover_rate_f"]),
                "is_new_high_60d": bool(m["is_new_high_60d"]) if m["is_new_high_60d"] is not None else False,
                "is_break_ma20": bool(m["is_break_ma20"]) if m["is_break_ma20"] is not None else False,
            })

        return items