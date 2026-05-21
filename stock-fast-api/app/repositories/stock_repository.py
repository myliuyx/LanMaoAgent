from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.exceptions import NotFoundException
from app.utils.safe_float import _safe_float, _clean_industry




class StockRepository:
    def __init__(self, db: Session):
        self.db = db

    def _stock_exists(self, symbol: str) -> None:
        """校验股票存在，不存在则抛 NotFoundException"""
        exists = self.db.execute(
            text("SELECT 1 FROM dwd_security_master WHERE symbol = :symbol"),
            {"symbol": symbol},
        ).fetchone()
        if not exists:
            raise NotFoundException(code=4041, message="stock not found")

    def get_profile(self, symbol: str) -> dict:
        """获取股票基础信息"""
        self._stock_exists(symbol)
        result = self.db.execute(
            text("""
                SELECT symbol, ticker, exchange, name, full_name,
                       security_type, list_board, list_date, delist_date,
                       status, is_st, industry_l1, industry_l2, area
                FROM dwd_security_master
                WHERE symbol = :symbol
            """),
            {"symbol": symbol},
        )
        row = result.fetchone()
        m = row._mapping

        # 清理 industry_l1 前缀（如 "C15酒、饮料..." → "酒、饮料..."）
        industry_l1_clean = _clean_industry(m["industry_l1"])

        # 从板块关联表读取板块列表
        boards_result = self.db.execute(
            text("""
                SELECT r.board_code, r.board_type, b.board_name
                FROM dwd_board_relation r
                JOIN dwd_board_master b ON r.board_code = b.board_code
                WHERE r.symbol = :symbol
                ORDER BY r.board_type
                LIMIT 20
            """),
            {"symbol": symbol},
        )
        board_rows = boards_result.mappings().fetchall()
        seen = set()
        boards = []
        for br in board_rows:
            if br["board_code"] in seen:
                continue
            seen.add(br["board_code"])
            boards.append({
                "board_code": br["board_code"],
                "board_name": br["board_name"],
                "board_type": br["board_type"],
            })

        return {
            "symbol": m["symbol"],
            "ticker": m["ticker"],
            "exchange": m["exchange"],
            "name": m["name"],
            "full_name": m["full_name"],
            "security_type": m["security_type"],
            "list_board": m["list_board"],
            "list_date": str(m["list_date"]) if m["list_date"] else None,
            "delist_date": str(m["delist_date"]) if m["delist_date"] else None,
            "status": m["status"],
            "is_st": bool(m["is_st"]) if m["is_st"] is not None else False,
            "industry_l1": industry_l1_clean or None,
            "industry_l2": m["industry_l2"],
            "area": m["area"],
            "boards": boards,
        }

    def get_latest(self, symbol: str) -> dict:
        """获取股票最新行情摘要（合并日线 + 财务 + 因子）"""
        self._stock_exists(symbol)

        # 1. 基础信息
        r = self.db.execute(
            text("""
                SELECT symbol, ticker, name, exchange, status, is_st,
                       industry_l1, industry_l2, area
                FROM dwd_security_master
                WHERE symbol = :symbol
            """),
            {"symbol": symbol},
        )
        pm = r.fetchone()._mapping

        industry_l1_clean = _clean_industry(pm["industry_l1"])

        # 2. 最新日线
        r = self.db.execute(
            text("""
                SELECT trade_date, close, pre_close, change_amount, change_pct,
                       turnover_rate_f, market_value, circulating_market_value,
                       pe_ttm, pb, ps_ttm, suspended_flag, is_limit_up, is_limit_down
                FROM dwd_stock_daily
                WHERE symbol = :symbol
                ORDER BY trade_date DESC
                LIMIT 1
            """),
            {"symbol": symbol},
        )
        row = r.fetchone()
        dm = row._mapping if row else {}

        # 3. 最新财务
        r = self.db.execute(
            text("""
                SELECT report_period, roe, revenue_yoy, net_profit_yoy
                FROM dwd_stock_financial_indicator
                WHERE symbol = :symbol
                ORDER BY report_period DESC
                LIMIT 1
            """),
            {"symbol": symbol},
        )
        row = r.fetchone()
        fr = row._mapping if row else {}

        # 4. 最新因子
        r = self.db.execute(
            text("""
                SELECT ma20, ma60, rsi_14, trend_score
                FROM dwd_stock_factor_daily
                WHERE symbol = :symbol
                ORDER BY trade_date DESC
                LIMIT 1
            """),
            {"symbol": symbol},
        )
        row = r.fetchone()
        fm = row._mapping if row else {}

        return {
            "symbol": pm["symbol"],
            "name": pm["name"],
            "industry_l2": pm.get("industry_l2"),
            "latest_trade_date": str(dm["trade_date"]) if dm.get("trade_date") else None,
            "close": _safe_float(dm.get("close")),
            "change_pct": _safe_float(dm.get("change_pct")),
            "turnover_rate": _safe_float(dm.get("turnover_rate_f")),
            "market_value": _safe_float(dm.get("market_value")),
            "pe_ttm": _safe_float(dm.get("pe_ttm")),
            "pb": _safe_float(dm.get("pb")),
            "ma20": _safe_float(fm.get("ma20")),
            "ma60": _safe_float(fm.get("ma60")),
            "rsi_14": _safe_float(fm.get("rsi_14")),
            "trend_score": _safe_float(fm.get("trend_score")),
            "roe": _safe_float(fr.get("roe")),
            "revenue_yoy": _safe_float(fr.get("revenue_yoy")),
            "net_profit_yoy": _safe_float(fr.get("net_profit_yoy")),
        }

    def search_stocks(self, keyword: str, limit: int) -> list:
        """股票搜索（支持名称和代码模糊匹配）"""
        result = self.db.execute(
            text("""
                SELECT symbol, name, exchange
                FROM dwd_security_master
                WHERE status = 'LISTED'
                  AND (name LIKE :kw OR ticker LIKE :kw)
                ORDER BY symbol
                LIMIT :limit
            """),
            {"kw": f"%{keyword}%", "limit": limit},
        )
        return [row._mapping for row in result.fetchall()]

    def get_daily(
        self,
        symbol: str,
        start_date: str | None,
        end_date: str | None,
        limit: int,
        adjust: str,
    ) -> list:
        """
        获取股票日线行情（ASC 顺序返回）。

        adjust 参数：
          - 'none' / 空：返回原始价格
          - 'qfq'：返回前复权价格 = close * adj_factor
        """
        self._stock_exists(symbol)

        sql = """
            SELECT d.trade_date, d.open, d.high, d.low, d.close,
                   d.pre_close, d.change_amount, d.change_pct,
                   d.volume, d.amount, d.turnover_rate, d.turnover_rate_f,
                   d.amplitude, d.market_value, d.circulating_market_value,
                   d.pe_ttm, d.pb, d.ps_ttm,
                   d.suspended_flag, d.is_limit_up, d.is_limit_down,
                   d.adj_factor
            FROM dwd_stock_daily d
            WHERE d.symbol = :symbol
        """
        params: dict = {"symbol": symbol}
        if start_date:
            sql += " AND d.trade_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            sql += " AND d.trade_date <= :end_date"
            params["end_date"] = end_date
        sql += " ORDER BY d.trade_date ASC LIMIT :limit"
        params["limit"] = limit

        result = self.db.execute(text(sql), params)
        rows = result.mappings().fetchall()

        records = []
        for m in rows:
            close = _safe_float(m["close"]) if m["close"] is not None else 0.0
            adj_factor = _safe_float(m["adj_factor"]) if m["adj_factor"] is not None else 1.0

            if adjust == "qfq":
                adj_close = close * adj_factor
                adj_open = float(m["open"]) * adj_factor
                adj_high = float(m["high"]) * adj_factor
                adj_low = float(m["low"]) * adj_factor
            else:
                adj_close = adj_open = adj_high = adj_low = None

            records.append({
                "trade_date": str(m["trade_date"]),
                "open": adj_open if adjust == "qfq" else _safe_float(m["open"]),
                "high": adj_high if adjust == "qfq" else _safe_float(m["high"]),
                "low": adj_low if adjust == "qfq" else _safe_float(m["low"]),
                "close": adj_close if adjust == "qfq" else close,
                "pre_close": _safe_float(m["pre_close"]),
                "change_amount": _safe_float(m["change_amount"]),
                "change_pct": _safe_float(m["change_pct"]),
                "volume": int(m["volume"]) if m["volume"] is not None else None,
                "amount": _safe_float(m["amount"]),
                "turnover_rate": _safe_float(m["turnover_rate"]),
                "turnover_rate_f": _safe_float(m["turnover_rate_f"]),
                "amplitude": _safe_float(m["amplitude"]),
                "market_value": _safe_float(m["market_value"]),
                "circ_market_value": _safe_float(m["circulating_market_value"]),
                "pe_ttm": _safe_float(m["pe_ttm"]),
                "pb": _safe_float(m["pb"]),
                "ps_ttm": _safe_float(m["ps_ttm"]),
                "suspended_flag": bool(m["suspended_flag"]) if m["suspended_flag"] is not None else False,
                "is_limit_up": bool(m["is_limit_up"]) if m["is_limit_up"] is not None else False,
                "is_limit_down": bool(m["is_limit_down"]) if m["is_limit_down"] is not None else False,
                "adj_factor": adj_factor,
            })
        return records

    def get_factors(
        self, symbol: str, trade_date: str | None, limit: int
    ) -> list:
        """
        获取技术因子数据（从 dwd_stock_factor_daily）。
        返回 dwd_stock_factor_daily 表中实际存在的字段：
        ma5/10/20/60/120/250, high_20/60, low_20/60,
        pct_5d/10d/20d/60d, volume_ma5/10,
        rsi_6/14, atr_14, macd_dif/dea/hist,
        is_new_high_60d, is_break_ma20, trend_score。
        """
        self._stock_exists(symbol)

        sql = """
            SELECT trade_date, ma5, ma10, ma20, ma60, ma120, ma250,
                   high_20, high_60, low_20, low_60,
                   pct_5d, pct_10d, pct_20d, pct_60d,
                   volume_ma5, volume_ma10,
                   rsi_6, rsi_14, atr_14,
                   macd_dif, macd_dea, macd_hist,
                   is_new_high_60d, is_break_ma20, trend_score
            FROM dwd_stock_factor_daily
            WHERE symbol = :symbol
        """
        params: dict = {"symbol": symbol}
        if trade_date:
            sql += " AND trade_date <= :trade_date"
            params["trade_date"] = trade_date
        sql += " ORDER BY trade_date DESC LIMIT :limit"
        params["limit"] = limit

        result = self.db.execute(text(sql), params)
        rows = result.mappings().fetchall()
        if not rows:
            return []

        return [
            {
                # 价格/日期
                "trade_date": str(m["trade_date"]),
                # 移动平均线
                "ma5": float(m["ma5"]) if m["ma5"] is not None else None,
                "ma10": float(m["ma10"]) if m["ma10"] is not None else None,
                "ma20": float(m["ma20"]) if m["ma20"] is not None else None,
                "ma60": float(m["ma60"]) if m["ma60"] is not None else None,
                "ma120": float(m["ma120"]) if m["ma120"] is not None else None,
                "ma250": float(m["ma250"]) if m["ma250"] is not None else None,
                # 高低价（之前遗漏的 9 个字段）
                "high_20": float(m["high_20"]) if m["high_20"] is not None else None,
                "high_60": float(m["high_60"]) if m["high_60"] is not None else None,
                "low_20": float(m["low_20"]) if m["low_20"] is not None else None,
                "low_60": float(m["low_60"]) if m["low_60"] is not None else None,
                # 涨跌幅
                "pct_5d": float(m["pct_5d"]) if m["pct_5d"] is not None else None,
                "pct_10d": float(m["pct_10d"]) if m["pct_10d"] is not None else None,
                "pct_20d": float(m["pct_20d"]) if m["pct_20d"] is not None else None,
                "pct_60d": float(m["pct_60d"]) if m["pct_60d"] is not None else None,
                # 量能均线
                "volume_ma5": float(m["volume_ma5"]) if m["volume_ma5"] is not None else None,
                "volume_ma10": float(m["volume_ma10"]) if m["volume_ma10"] is not None else None,
                # RSI / ATR
                "rsi_6": float(m["rsi_6"]) if m["rsi_6"] is not None else None,
                "rsi_14": float(m["rsi_14"]) if m["rsi_14"] is not None else None,
                "atr_14": float(m["atr_14"]) if m["atr_14"] is not None else None,
                # MACD
                "macd_dif": float(m["macd_dif"]) if m["macd_dif"] is not None else None,
                "macd_dea": float(m["macd_dea"]) if m["macd_dea"] is not None else None,
                "macd_hist": float(m["macd_hist"]) if m["macd_hist"] is not None else None,
                # 信号
                "is_new_high_60d": bool(m["is_new_high_60d"]) if m["is_new_high_60d"] is not None else False,
                "is_break_ma20": bool(m["is_break_ma20"]) if m["is_break_ma20"] is not None else False,
                "trend_score": float(m["trend_score"]) if m["trend_score"] is not None else None,
            }
            for m in rows
        ]

    def get_finance(self, symbol: str, limit: int) -> list:
        """获取财务指标数据（从 dwd_stock_financial_indicator）"""
        self._stock_exists(symbol)

        result = self.db.execute(
            text("""
                SELECT report_period, report_type, announce_date,
                       eps, bps, roe, roa,
                       gross_margin, net_margin,
                       debt_to_asset, current_ratio, quick_ratio,
                       revenue, net_profit,
                       revenue_yoy, net_profit_yoy, ocf
                FROM dwd_stock_financial_indicator
                WHERE symbol = :symbol
                ORDER BY report_period DESC
                LIMIT :limit
            """),
            {"symbol": symbol, "limit": limit},
        )
        rows = result.mappings().fetchall()
        if not rows:
            return []

        return [
            {
                "report_period": str(m["report_period"]),
                "report_type": m["report_type"],
                "announce_date": str(m["announce_date"]) if m["announce_date"] else None,
                "eps": float(m["eps"]) if m["eps"] is not None else None,
                "bps": float(m["bps"]) if m["bps"] is not None else None,
                "roe": float(m["roe"]) if m["roe"] is not None else None,
                "roa": float(m["roa"]) if m["roa"] is not None else None,
                "gross_margin": float(m["gross_margin"]) if m["gross_margin"] is not None else None,
                "net_margin": float(m["net_margin"]) if m["net_margin"] is not None else None,
                "debt_to_asset": float(m["debt_to_asset"]) if m["debt_to_asset"] is not None else None,
                "current_ratio": float(m["current_ratio"]) if m["current_ratio"] is not None else None,
                "quick_ratio": float(m["quick_ratio"]) if m["quick_ratio"] is not None else None,
                "revenue": float(m["revenue"]) if m["revenue"] is not None else None,
                "net_profit": float(m["net_profit"]) if m["net_profit"] is not None else None,
                "revenue_yoy": float(m["revenue_yoy"]) if m["revenue_yoy"] is not None else None,
                "net_profit_yoy": float(m["net_profit_yoy"]) if m["net_profit_yoy"] is not None else None,
                "ocf": float(m["ocf"]) if m["ocf"] is not None else None,
            }
            for m in rows
        ]

    def get_boards(self, symbol: str) -> list:
        """获取股票所属板块（从 dwd_board_relation + dwd_board_master）"""
        self._stock_exists(symbol)

        result = self.db.execute(
            text("""
                SELECT r.board_code, r.board_type, b.board_name
                FROM dwd_board_relation r
                JOIN dwd_board_master b ON r.board_code = b.board_code
                WHERE r.symbol = :symbol
                ORDER BY r.board_type
                LIMIT 50
            """),
            {"symbol": symbol},
        )
        rows = result.mappings().fetchall()
        if not rows:
            return []

        # 按 board_code 去重（无 trade_date 维度，直接去重）
        seen = set()
        records = []
        for m in rows:
            if m["board_code"] in seen:
                continue
            seen.add(m["board_code"])
            records.append({
                "board_code": m["board_code"],
                "board_name": m["board_name"],
                "board_type": m["board_type"],
            })
        return records

    def get_adjust_factors(self, symbol: str, start_date: str | None, end_date: str | None, limit: int) -> list:
        """
        获取复权因子历史。
        数据来源：dwd_stock_adjust_factor
        """
        self._stock_exists(symbol)

        sql = """
            SELECT trade_date, adj_factor, forward_adj_close, backward_adj_close,
                   cash_dividend, stock_dividend, rights_issue_ratio, event_type
            FROM dwd_stock_adjust_factor
            WHERE symbol = :symbol
        """
        params: dict = {"symbol": symbol}
        if start_date:
            sql += " AND trade_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            sql += " AND trade_date <= :end_date"
            params["end_date"] = end_date
        sql += " ORDER BY trade_date DESC LIMIT :limit"
        params["limit"] = limit

        result = self.db.execute(text(sql), params)
        rows = result.mappings().fetchall()

        return [
            {
                "trade_date": str(m["trade_date"]),
                "adj_factor": _safe_float(m["adj_factor"]),
                "forward_adj_close": _safe_float(m["forward_adj_close"]),
                "backward_adj_close": _safe_float(m["backward_adj_close"]),
                "cash_dividend": _safe_float(m["cash_dividend"]),
                "stock_dividend": _safe_float(m["stock_dividend"]),
                "rights_issue_ratio": _safe_float(m["rights_issue_ratio"]),
                "event_type": m["event_type"],
            }
            for m in rows
        ]

    # 注意：get_coverage 已移除（查询 etl_data_coverage 空表）。
    # 正确接口为 /coverage/{symbol}，由 CoverageRepository.get_detail 提供。
