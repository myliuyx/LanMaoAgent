from pydantic import BaseModel, Field


class WatchlistAnalysisRequest(BaseModel):
    symbols: list[str] = Field(..., max_length=100, description="股票代码列表，最多100个")


class WatchlistStockItem(BaseModel):
    symbol: str
    name: str
    close: float | None
    change_pct: float | None
    turnover_rate: float | None
    high_52w: float | None
    low_52w: float | None
    near_high: bool
    near_low: bool
    ma5: float | None
    ma10: float | None
    ma20: float | None
    ma60: float | None
    bullish: bool
    bearish: bool
    volume_spike: bool
    momentum: float | None
    signals: list[str]


class WatchlistSummary(BaseModel):
    total: int
    up_count: int
    down_count: int
    near_high_count: int
    near_low_count: int
    bullish_count: int
    volume_alert_count: int
    up_rate: float


class WatchlistAnalysisData(BaseModel):
    summary: WatchlistSummary
    stocks: list[WatchlistStockItem]


class DashboardSummaryData(BaseModel):
    latest_trade_date: str
    is_trade_day: bool
    stock_count: int
    daily_record_count: int
    finance_record_count: int
    factor_record_count: int
    today_job_success_count: int
    today_job_failed_count: int
    selection_count: int
