import math
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.utils.safe_float import _safe_float


class DashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_summary(self) -> dict:
        """
        获取首页摘要数据。
        所有日期查询均限制为 <= CURRENT_DATE，避免返回未来日期。
        """
        result = {}

        # 1. 最新交易日（限制不超过今天，避免 dwd_trade_calendar 包含未来日期）
        r = self.db.execute(
            text("""
                SELECT MAX(trade_date)
                FROM dwd_stock_daily
                WHERE trade_date <= CURRENT_DATE
            """)
        )
        result["latest_trade_date"] = str(r.fetchone()[0] or "")

        # 2. 今日是否为交易日（使用 Asia/Shanghai 时区的今日日期）
        r = self.db.execute(
            text("""
                SELECT is_open
                FROM dwd_trade_calendar
                WHERE trade_date = (CURRENT_DATE AT TIME ZONE 'Asia/Shanghai')::date
            """)
        )
        row = r.fetchone()
        result["is_trade_day"] = bool(row[0]) if row else False

        # 3. 股票总数
        r = self.db.execute(
            text("SELECT COUNT(*) FROM dwd_security_master WHERE status = 'LISTED'")
        )
        result["stock_count"] = r.fetchone()[0] or 0

        # 4. 日线记录总数
        r = self.db.execute(text("SELECT COUNT(*) FROM dwd_stock_daily"))
        result["daily_record_count"] = r.fetchone()[0] or 0

        # 5. 财务指标记录总数
        r = self.db.execute(text("SELECT COUNT(*) FROM dwd_stock_financial_indicator"))
        result["finance_record_count"] = r.fetchone()[0] or 0

        # 6. 技术因子记录总数
        r = self.db.execute(text("SELECT COUNT(*) FROM dwd_stock_factor_daily"))
        result["factor_record_count"] = r.fetchone()[0] or 0

        # 7. 今日 ETL 成功任务数
        r = self.db.execute(
            text("""
                SELECT COUNT(*)
                FROM etl_job_run
                WHERE DATE(created_at AT TIME ZONE 'Asia/Shanghai') =
                      (CURRENT_DATE AT TIME ZONE 'Asia/Shanghai')::date
                  AND status = 'SUCCESS'
            """)
        )
        result["today_job_success_count"] = r.fetchone()[0] or 0

        # 8. 今日 ETL 失败任务数
        r = self.db.execute(
            text("""
                SELECT COUNT(*)
                FROM etl_job_run
                WHERE DATE(created_at AT TIME ZONE 'Asia/Shanghai') =
                      (CURRENT_DATE AT TIME ZONE 'Asia/Shanghai')::date
                  AND status = 'FAILED'
            """)
        )
        result["today_job_failed_count"] = r.fetchone()[0] or 0

        # 9. 选股宽表记录数（mart_stock_selection_daily 为空时为 0）
        r = self.db.execute(text("SELECT COUNT(*) FROM mart_stock_selection_daily"))
        result["selection_count"] = r.fetchone()[0] or 0

        return result

    def get_recent_jobs(self, limit: int) -> list:
        """
        返回最近 N 条 ETL 任务（从 etl_job_run）。
        返回字段与 JobItem schema 对齐，不包含 created_at。
        """
        result = self.db.execute(
            text("""
                SELECT id, job_name, biz_date, status,
                       start_time, end_time, duration_ms,
                       rows_raw, rows_written, error_message
                FROM etl_job_run
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"limit": limit},
        )
        rows = result.fetchall()
        return [
            {
                "id": row._mapping["id"],
                "job_name": row._mapping["job_name"],
                "biz_date": str(row._mapping["biz_date"]) if row._mapping["biz_date"] else None,
                "status": row._mapping["status"],
                "start_time": row._mapping["start_time"].isoformat() if row._mapping["start_time"] else None,
                "end_time": row._mapping["end_time"].isoformat() if row._mapping["end_time"] else None,
                "duration_ms": row._mapping["duration_ms"],
                "rows_raw": row._mapping["rows_raw"],
                "rows_written": row._mapping["rows_written"],
                "error_message": row._mapping["error_message"],
            }
            for row in rows
        ]

    def get_coverage_summary(self) -> dict:
        """数据覆盖摘要（与 /coverage/summary 字段对齐）。"""
        r = self.db.execute(text("SELECT COUNT(*) FROM dwd_security_master WHERE status = 'LISTED'"))
        total_symbols = r.fetchone()[0] or 0

        r = self.db.execute(text("""
            SELECT COUNT(DISTINCT symbol)
            FROM dwd_stock_daily
            WHERE trade_date = (SELECT MAX(trade_date) FROM dwd_stock_daily)
              AND trade_date <= CURRENT_DATE
        """))
        daily_fully = r.fetchone()[0] or 0

        r = self.db.execute(text("SELECT COUNT(DISTINCT symbol) FROM dwd_stock_financial_indicator"))
        finance_fully = r.fetchone()[0] or 0

        r = self.db.execute(text("SELECT COUNT(DISTINCT symbol) FROM dwd_stock_adjust_factor"))
        adj_fully = r.fetchone()[0] or 0

        return {
            "total_symbols": total_symbols,
            "daily_fully_covered_symbols": daily_fully,
            "financial_fully_covered_symbols": finance_fully,
            "adjust_factor_fully_covered_symbols": adj_fully,
        }

    def watchlist_analysis(self, symbols: list[str]) -> dict:
        """
        自选股技术面分析。

        数据来源：
        - dwd_stock_daily: 行情数据（close, change_pct, turnover_rate, volume, high, low）
        - dwd_stock_factor_daily: 技术因子（ma5/10/20/60, high_20/60, low_20/60）
        - dwd_security_master: 股票名称
        """
        if not symbols:
            return {
                "summary": {
                    "total": 0, "up_count": 0, "down_count": 0,
                    "near_high_count": 0, "near_low_count": 0,
                    "bullish_count": 0, "volume_alert_count": 0, "up_rate": 0.0,
                },
                "stocks": [],
            }

        # 1. 获取所有股票的名称和基本信息
        names_map = {}
        result = self.db.execute(
            text("""
                SELECT symbol, name FROM dwd_security_master
                WHERE symbol = ANY(:symbols)
            """),
            {"symbols": symbols}
        )
        for row in result:
            names_map[row._mapping["symbol"]] = row._mapping["name"]

        # 2. 获取最新日线数据（每个symbol的最新一条）
        latest_daily = {}
        result = self.db.execute(
            text("""
                SELECT d.symbol, d.close, d.change_pct, d.turnover_rate_f,
                       d.volume, d.high, d.low
                FROM (
                    SELECT symbol, close, change_pct, turnover_rate_f, volume, high, low,
                           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) as rn
                    FROM dwd_stock_daily
                    WHERE symbol = ANY(:symbols) AND trade_date <= CURRENT_DATE
                ) d
                WHERE d.rn = 1
            """),
            {"symbols": symbols}
        )
        for row in result:
            latest_daily[row._mapping["symbol"]] = row._mapping

        # 3. 获取20日均量用于volume_spike计算
        volume_20d_avg = {}
        result = self.db.execute(
            text("""
                SELECT symbol, AVG(volume)::bigint as avg_volume
                FROM (
                    SELECT symbol, volume,
                           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) as rn
                    FROM dwd_stock_daily
                    WHERE symbol = ANY(:symbols) AND trade_date <= CURRENT_DATE
                ) sub
                WHERE rn <= 20
                GROUP BY symbol
            """),
            {"symbols": symbols}
        )
        for row in result:
            volume_20d_avg[row._mapping["symbol"]] = row._mapping["avg_volume"]

        # 4. 获取52周高低价（取约252个交易日的最高价和最低价）
        high_52w_map = {}
        result = self.db.execute(
            text("""
                SELECT symbol, MAX(high) as high_52w, MIN(low) as low_52w
                FROM (
                    SELECT symbol, high, low,
                           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) as rn
                    FROM dwd_stock_daily
                    WHERE symbol = ANY(:symbols) AND trade_date <= CURRENT_DATE
                ) sub
                WHERE rn <= 252
                GROUP BY symbol
            """),
            {"symbols": symbols}
        )
        for row in result:
            high_52w_map[row._mapping["symbol"]] = {
                "high_52w": row._mapping["high_52w"],
                "low_52w": row._mapping["low_52w"],
            }

        # 5. 获取最新技术因子（ma5/ma10/ma20/ma60, high_20/60, low_20/60）
        factors_map = {}
        result = self.db.execute(
            text("""
                SELECT f.symbol, f.ma5, f.ma10, f.ma20, f.ma60,
                       f.high_20, f.high_60, f.low_20, f.low_60
                FROM (
                    SELECT symbol, ma5, ma10, ma20, ma60, high_20, high_60, low_20, low_60,
                           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) as rn
                    FROM dwd_stock_factor_daily
                    WHERE symbol = ANY(:symbols) AND trade_date <= CURRENT_DATE
                ) f
                WHERE f.rn = 1
            """),
            {"symbols": symbols}
        )
        for row in result:
            factors_map[row._mapping["symbol"]] = row._mapping

        # 6. 计算20日动量（从dwd_stock_daily计算近20日价格变化）
        momentum_final = {}
        result = self.db.execute(
            text("""
                WITH ranked AS (
                    SELECT symbol, close,
                           LAG(close, 20) OVER (PARTITION BY symbol ORDER BY trade_date) as close_20d_ago,
                           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) as rn
                    FROM dwd_stock_daily
                    WHERE symbol = ANY(:symbols) AND trade_date <= CURRENT_DATE
                )
                SELECT symbol, close, close_20d_ago
                FROM ranked
                WHERE rn = 1 AND close_20d_ago IS NOT NULL AND close_20d_ago != 0
            """),
            {"symbols": symbols}
        )
        for row in result:
            m = row._mapping
            momentum_final[m["symbol"]] = (float(m["close"]) - float(m["close_20d_ago"])) / float(m["close_20d_ago"]) * 100

        # 7. 构建每个股票的分析结果
        stocks = []
        up_count = 0
        near_high_count = 0
        near_low_count = 0
        bullish_count = 0
        volume_alert_count = 0

        for symbol in symbols:
            name = names_map.get(symbol, symbol)
            daily = latest_daily.get(symbol, {})
            factors = factors_map.get(symbol, {})
            high_52w_data = high_52w_map.get(symbol, {})
            vol_avg = volume_20d_avg.get(symbol, 0)
            momentum = momentum_final.get(symbol)

            close = _safe_float(daily.get("close"))
            change_pct = _safe_float(daily.get("change_pct"))
            turnover_rate = _safe_float(daily.get("turnover_rate_f"))
            volume = daily.get("volume")
            high_52w = _safe_float(high_52w_data.get("high_52w"))
            low_52w = _safe_float(high_52w_data.get("low_52w"))
            ma5 = _safe_float(factors.get("ma5"))
            ma10 = _safe_float(factors.get("ma10"))
            ma20 = _safe_float(factors.get("ma20"))
            ma60 = _safe_float(factors.get("ma60"))

            # 计算 near_high / near_low
            near_high = False
            near_low = False
            if close is not None and high_52w is not None and high_52w > 0:
                near_high = close >= high_52w * 0.9
            if close is not None and low_52w is not None and low_52w > 0:
                near_low = close <= low_52w * 1.1

            # 均线多头排列：MA5 > MA10 > MA20 > MA60，且 price > MA5
            bullish = False
            bearish = False
            if all(x is not None for x in [ma5, ma10, ma20, ma60, close]):
                if ma5 > ma10 > ma20 > ma60 and close > ma5:
                    bullish = True
                elif ma5 < ma10 < ma20 < ma60 and close < ma5:
                    bearish = True

            # 成交量异常放大：今日量 > 20日均量 * 2
            volume_spike = False
            if volume is not None and vol_avg is not None and vol_avg > 0:
                volume_spike = volume > vol_avg * 2

            # 生成信号标签
            signals = []
            if bullish:
                signals.append("均线多头排列")
            if bearish:
                signals.append("均线空头排列")
            if near_high:
                signals.append("接近52周高位")
            if near_low:
                signals.append("接近52周低位")
            if volume_spike:
                signals.append("成交量异常放大")
            if momentum is not None:
                if momentum > 5:
                    signals.append(f"月动能强劲({momentum:.1f}%)")
                elif momentum < -5:
                    signals.append(f"月动能疲弱({momentum:.1f}%)")

            # 统计
            if change_pct is not None:
                if change_pct > 0:
                    up_count += 1
            if near_high:
                near_high_count += 1
            if near_low:
                near_low_count += 1
            if bullish:
                bullish_count += 1
            if volume_spike:
                volume_alert_count += 1

            stocks.append({
                "symbol": symbol,
                "name": name,
                "close": close,
                "change_pct": change_pct,
                "turnover_rate": turnover_rate,
                "high_52w": high_52w,
                "low_52w": low_52w,
                "near_high": near_high,
                "near_low": near_low,
                "ma5": ma5,
                "ma10": ma10,
                "ma20": ma20,
                "ma60": ma60,
                "bullish": bullish,
                "bearish": bearish,
                "volume_spike": volume_spike,
                "momentum": _safe_float(momentum),
                "signals": signals,
            })

        total = len(stocks)
        up_rate = (up_count / total * 100) if total > 0 else 0.0

        return {
            "summary": {
                "total": total,
                "up_count": up_count,
                "down_count": total - up_count,
                "near_high_count": near_high_count,
                "near_low_count": near_low_count,
                "bullish_count": bullish_count,
                "volume_alert_count": volume_alert_count,
                "up_rate": round(up_rate, 1),
            },
            "stocks": stocks,
        }
