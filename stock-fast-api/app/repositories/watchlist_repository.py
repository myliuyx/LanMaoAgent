from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.exceptions import NotFoundException
from app.utils.safe_float import _safe_float


class WatchlistRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_watchlist(self, user_id: str, page: int, page_size: int) -> dict:
        """
        获取自选股列表，关联行情和趋势评分。
        - name, exchange → dwd_security_master
        - close, change_pct, turnover_rate, amplitude, pe_ttm, pb → dwd_stock_daily（最新一条）
        - trend_score → mart_stock_selection_daily（如无数据则 null）
        - 52周高低价、MA5 → dwd_stock_daily（过去252天/5天聚合）
        """
        offset = (page - 1) * page_size

        # 计数
        count_sql = text("""
            SELECT COUNT(*)
            FROM mart_user_watchlist w
            WHERE w.user_id = :user_id
        """)
        total = self.db.execute(count_sql, {"user_id": user_id}).fetchone()[0]

        # 数据查询 - 包含52周高低价、MA5、amplitude、pe_ttm、pb
        data_sql = text("""
            SELECT
                w.symbol,
                m.name,
                m.exchange,
                w.added_at,
                d.close AS close,
                d.change_pct,
                d.turnover_rate,
                d.amplitude,
                d.pe_ttm,
                d.pb,
                s.trend_score,
                p52.price_52w_high,
                p52.price_52w_low,
                ma5.ma5
            FROM mart_user_watchlist w
            JOIN dwd_security_master m ON w.symbol = m.symbol
            LEFT JOIN LATERAL (
                SELECT close, change_pct, turnover_rate, amplitude, pe_ttm, pb
                FROM dwd_stock_daily
                WHERE symbol = w.symbol
                ORDER BY trade_date DESC
                LIMIT 1
            ) d ON true
            LEFT JOIN LATERAL (
                SELECT trend_score
                FROM mart_stock_selection_daily
                WHERE symbol = w.symbol
                ORDER BY trade_date DESC
                LIMIT 1
            ) s ON true
            LEFT JOIN LATERAL (
                SELECT
                    MAX(close) AS price_52w_high,
                    MIN(close) AS price_52w_low
                FROM dwd_stock_daily
                WHERE symbol = w.symbol
                  AND trade_date <= CURRENT_DATE
                  AND trade_date >= CURRENT_DATE - INTERVAL '252 days'
            ) p52 ON true
            LEFT JOIN LATERAL (
                SELECT AVG(close) AS ma5
                FROM (
                    SELECT close
                    FROM dwd_stock_daily
                    WHERE symbol = w.symbol
                      AND trade_date <= CURRENT_DATE
                    ORDER BY trade_date DESC
                    LIMIT 5
                ) sub
            ) ma5 ON true
            WHERE w.user_id = :user_id
            ORDER BY w.added_at DESC
            LIMIT :limit OFFSET :offset
        """)
        result = self.db.execute(data_sql, {
            "user_id": user_id,
            "limit": page_size,
            "offset": offset,
        })
        rows = result.fetchall()

        items = []
        for row in rows:
            close = float(row._mapping["close"]) if row._mapping["close"] else None
            price_52w_high = float(row._mapping["price_52w_high"]) if row._mapping["price_52w_high"] else None
            price_52w_low = float(row._mapping["price_52w_low"]) if row._mapping["price_52w_low"] else None
            ma5 = float(row._mapping["ma5"]) if row._mapping["ma5"] else None

            # 计算 price_percentile: (close - 52w_low) / (52w_high - 52w_low) * 100
            price_percentile = None
            if close is not None and price_52w_high is not None and price_52w_low is not None:
                if price_52w_high != price_52w_low:
                    price_percentile = (close - price_52w_low) / (price_52w_high - price_52w_low) * 100

            # 计算 dist_to_52w_high_pct: (close - 52w_high) / 52w_high * 100
            dist_to_52w_high_pct = None
            if close is not None and price_52w_high is not None:
                dist_to_52w_high_pct = (close - price_52w_high) / price_52w_high * 100

            # 计算 dist_to_52w_low_pct: (close - 52w_low) / 52w_low * 100
            dist_to_52w_low_pct = None
            if close is not None and price_52w_low is not None:
                dist_to_52w_low_pct = (close - price_52w_low) / price_52w_low * 100

            # 计算 price_vs_ma5_pct: (close - ma5) / ma5 * 100
            price_vs_ma5_pct = None
            if close is not None and ma5 is not None:
                price_vs_ma5_pct = (close - ma5) / ma5 * 100

            items.append({
                "symbol": row._mapping["symbol"],
                "name": row._mapping["name"],
                "exchange": row._mapping["exchange"],
                "added_at": row._mapping["added_at"].isoformat() if row._mapping["added_at"] else None,
                "close": close,
                "change_pct": _safe_float(row._mapping["change_pct"]),
                "turnover_rate": _safe_float(row._mapping["turnover_rate"]),
                "trend_score": _safe_float(row._mapping["trend_score"]),
                "price_52w_high": price_52w_high,
                "price_52w_low": price_52w_low,
                "price_percentile": round(price_percentile, 2) if price_percentile is not None else None,
                "dist_to_52w_high_pct": round(dist_to_52w_high_pct, 2) if dist_to_52w_high_pct is not None else None,
                "dist_to_52w_low_pct": round(dist_to_52w_low_pct, 2) if dist_to_52w_low_pct is not None else None,
                "ma5": ma5,
                "price_vs_ma5_pct": round(price_vs_ma5_pct, 2) if price_vs_ma5_pct is not None else None,
                "amplitude": _safe_float(row._mapping["amplitude"]),
                "pe_ttm": _safe_float(row._mapping["pe_ttm"]),
                "pb": _safe_float(row._mapping["pb"]),
            })

        return {
            "list": items,
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    def add_watchlist(self, user_id: str, symbol: str) -> dict:
        """
        添加股票到自选股。
        返回 added_at 时间。
        """
        added_at = datetime.now()
        sql = text("""
            INSERT INTO mart_user_watchlist (user_id, symbol, added_at)
            VALUES (:user_id, :symbol, :added_at)
            RETURNING added_at
        """)
        result = self.db.execute(sql, {
            "user_id": user_id,
            "symbol": symbol,
            "added_at": added_at,
        })
        self.db.commit()
        row = result.fetchone()
        return {
            "symbol": symbol,
            "added_at": row._mapping["added_at"].isoformat() if row._mapping["added_at"] else added_at.isoformat(),
        }

    def delete_watchlist(self, user_id: str, symbol: str) -> bool:
        """
        从自选股删除。
        返回是否删除成功（未找到返回 False）。
        """
        sql = text("""
            DELETE FROM mart_user_watchlist
            WHERE user_id = :user_id AND symbol = :symbol
        """)
        result = self.db.execute(sql, {"user_id": user_id, "symbol": symbol})
        self.db.commit()
        return result.rowcount > 0

    def check_watchlist(self, user_id: str, symbol: str) -> bool:
        """
        检查股票是否在自选股中。
        """
        sql = text("""
            SELECT 1 FROM mart_user_watchlist
            WHERE user_id = :user_id AND symbol = :symbol
            LIMIT 1
        """)
        result = self.db.execute(sql, {"user_id": user_id, "symbol": symbol})
        return result.fetchone() is not None

    def is_stock_exists(self, symbol: str) -> bool:
        """
        检查股票是否在 dwd_security_master 中且状态为 LISTED。
        """
        sql = text("""
            SELECT 1 FROM dwd_security_master
            WHERE symbol = :symbol AND status = 'LISTED'
            LIMIT 1
        """)
        result = self.db.execute(sql, {"symbol": symbol})
        return result.fetchone() is not None
