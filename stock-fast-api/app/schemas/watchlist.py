from pydantic import BaseModel, Field
from app.schemas.common import PageData


class WatchlistQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class WatchlistItem(BaseModel):
    symbol: str
    name: str
    exchange: str
    added_at: str
    close: float | None = None
    change_pct: float | None = None
    turnover_rate: float | None = None
    trend_score: float | None = None
    # 52周价格区间
    price_52w_high: float | None = None
    price_52w_low: float | None = None
    price_percentile: float | None = None
    dist_to_52w_high_pct: float | None = None
    dist_to_52w_low_pct: float | None = None
    # MA5
    ma5: float | None = None
    price_vs_ma5_pct: float | None = None
    # 振幅和估值
    amplitude: float | None = None
    pe_ttm: float | None = None
    pb: float | None = None


class WatchlistQueryData(PageData[WatchlistItem]):
    pass


class WatchlistAddRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16)


class WatchlistAddData(BaseModel):
    symbol: str
    added_at: str


class WatchlistDeleteData(BaseModel):
    symbol: str


class WatchlistCheckData(BaseModel):
    symbol: str
    in_watchlist: bool
