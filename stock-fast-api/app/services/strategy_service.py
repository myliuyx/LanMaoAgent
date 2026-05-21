from sqlalchemy.orm import Session

from app.repositories.strategy_repository import StrategyRepository, STRATEGY_METADATA, _safe_float
from app.schemas.strategy import (
    StrategyInfo,
    StrategyQueryRequest,
    StrategyStockItem,
    StrategyStats,
    StockAnalyzeRequest,
)


class StrategyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StrategyRepository(db)

    def list_strategies(self) -> list[StrategyInfo]:
        """返回全部9个策略的元信息"""
        return [
            StrategyInfo(**meta)
            for meta in STRATEGY_METADATA.values()
        ]

    def get_strategy_info(self, strategy_id: str) -> StrategyInfo:
        """返回指定策略的元信息"""
        meta = STRATEGY_METADATA.get(strategy_id)
        if not meta:
            raise ValueError(f"Unknown strategy: {strategy_id}")
        return StrategyInfo(**meta)

    def query(self, req: StrategyQueryRequest) -> dict:
        """
        执行策略查询，返回匹配的股票列表。
        """
        # 校验策略存在
        if req.strategy_id not in STRATEGY_METADATA:
            raise ValueError(f"Unknown strategy: {req.strategy_id}")

        items, total, stats = self.repo.execute_strategy(
            strategy_id=req.strategy_id,
            trade_date=req.trade_date,
            limit=req.limit,
        )

        strategy_info = StrategyInfo(**STRATEGY_METADATA[req.strategy_id])

        return {
            "strategy": strategy_info,
            "items": items,
            "total": total,
            "stats": stats,
        }

    def analyze(self, req: StockAnalyzeRequest) -> dict:
        """
        问股分析：给定一只股票，用9种策略分别分析它。
        """
        # 默认用最近交易日
        trade_date = req.trade_date
        if not trade_date:
            result = self.db.execute(
                __import__("sqlalchemy").text(
                    "SELECT MAX(trade_date) FROM dwd_stock_daily WHERE symbol = :symbol AND trade_date <= CURRENT_DATE"
                ),
                {"symbol": req.symbol},
            )
            row = result.fetchone()
            if not row or not row[0]:
                raise ValueError(f"No trading data found for {req.symbol}")
            trade_date = str(row[0])

        results = self.repo.analyze_stock(req.symbol, trade_date)

        # 获取股票基础信息
        sql = __import__("sqlalchemy").text("""
            SELECT m.symbol, m.name, m.exchange,
                   d.close, d.change_pct, d.turnover_rate_f as turnover_rate, d.volume_ratio,
                   f.ma5, f.ma10, f.ma20, f.trend_score
            FROM dwd_security_master m
            LEFT JOIN dwd_stock_daily d ON d.symbol = m.symbol AND d.trade_date = :trade_date
            LEFT JOIN dwd_stock_factor_daily f ON f.symbol = m.symbol AND f.trade_date = :trade_date
            WHERE m.symbol = :symbol
        """)
        row = self.db.execute(sql, {"symbol": req.symbol, "trade_date": trade_date}).mappings().fetchone()
        if not row:
            raise ValueError(f"Stock {req.symbol} not found")

        float_fields = ("close", "change_pct", "turnover_rate", "ma5", "ma10", "ma20", "volume_ratio", "trend_score")
        float_row = {k: (_safe_float(v) if k in float_fields and v is not None else v) for k, v in row.items()}

        return {
            "symbol": float_row["symbol"],
            "name": float_row["name"],
            "exchange": float_row["exchange"],
            "close": float_row["close"],
            "change_pct": float_row["change_pct"],
            "turnover_rate": float_row["turnover_rate"],
            "ma5": float_row["ma5"],
            "ma10": float_row["ma10"],
            "ma20": float_row["ma20"],
            "volume_ratio": float_row["volume_ratio"],
            "trend_score": float_row["trend_score"],
            "trade_date": trade_date,
            "results": results,
        }