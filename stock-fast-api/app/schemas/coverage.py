from pydantic import BaseModel


class CoverageSummaryData(BaseModel):
    total_symbols: int
    daily_fully_covered_symbols: int
    financial_fully_covered_symbols: int
    adjust_factor_fully_covered_symbols: int
    latest_daily_trade_date: str | None = None
    latest_financial_report_period: str | None = None
