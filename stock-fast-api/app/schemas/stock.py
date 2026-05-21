from typing import Optional
from pydantic import BaseModel


class StockProfileData(BaseModel):
    symbol: str
    ticker: str
    exchange: str
    name: str
    full_name: Optional[str] = None
    security_type: str = "stock"
    list_board: Optional[str] = None
    list_date: Optional[str] = None
    delist_date: Optional[str] = None
    status: str = "listed"
    is_st: bool = False
    industry_l1: Optional[str] = None
    industry_l2: Optional[str] = None
    area: Optional[str] = None


class StockLatestData(BaseModel):
    symbol: str
    name: str
    latest_trade_date: str
    close: Optional[float] = None
    change_pct: Optional[float] = None
    turnover_rate: Optional[float] = None
    market_value: Optional[float] = None
    pe_ttm: Optional[float] = None
    pb: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    rsi_14: Optional[float] = None
    trend_score: Optional[float] = None
    roe: Optional[float] = None
    revenue_yoy: Optional[float] = None
    net_profit_yoy: Optional[float] = None


class AdjustFactorItem(BaseModel):
    trade_date: str
    adj_factor: Optional[float] = None
    forward_adj_close: Optional[float] = None
    backward_adj_close: Optional[float] = None
    cash_dividend: Optional[float] = None
    stock_dividend: Optional[float] = None
    rights_issue_ratio: Optional[float] = None
    event_type: Optional[str] = None
