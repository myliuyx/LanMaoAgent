from typing import Optional, Literal
from pydantic import BaseModel, Field
from app.schemas.common import PageData


class SelectionTopItem(BaseModel):
    symbol: str
    name: str
    exchange: str
    industry_l1: Optional[str] = None
    selection_count: int
    avg_trend_score: Optional[float] = None
    avg_roe: Optional[float] = None
    avg_revenue_yoy: Optional[float] = None
    avg_net_profit_yoy: Optional[float] = None
    high_60d_count: int
    break_ma20_count: int
    latest_date: Optional[str] = None
    close: Optional[float] = None
    change_pct: Optional[float] = None
    turnover_rate: Optional[float] = None
    is_new_high_60d: bool
    is_break_ma20: bool


class SelectionFilters(BaseModel):
    keyword: Optional[str] = None
    exchange: Optional[str] = None
    is_st: Optional[bool] = None
    industry_l1: Optional[str] = None

    market_value_min: Optional[float] = None
    market_value_max: Optional[float] = None
    turnover_rate_min: Optional[float] = None
    turnover_rate_max: Optional[float] = None
    roe_min: Optional[float] = None
    revenue_yoy_min: Optional[float] = None
    net_profit_yoy_min: Optional[float] = None
    is_new_high_60d: Optional[bool] = None
    is_break_ma20: Optional[bool] = None
    trend_score_min: Optional[float] = None


class SelectionQueryRequest(BaseModel):
    trade_date: str
    filters: SelectionFilters = Field(default_factory=SelectionFilters)
    sort_by: Optional[str] = "trend_score"
    sort_order: Literal["asc", "desc"] = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class SelectionItem(BaseModel):
    symbol: str
    name: str
    exchange: str
    industry_l1: Optional[str] = None
    close: Optional[float] = None
    change_pct: Optional[float] = None
    turnover_rate: Optional[float] = None
    market_value: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    is_new_high_60d: Optional[bool] = None
    trend_score: Optional[float] = None
    is_st: bool
    roe: Optional[float] = None
    revenue_yoy: Optional[float] = None
    net_profit_yoy: Optional[float] = None


class SelectionQueryData(PageData[SelectionItem]):
    pass
