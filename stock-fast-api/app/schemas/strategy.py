from typing import Optional, Literal
from pydantic import BaseModel, Field


class StrategyEnum(str):
    BOTTOM_VOLUME = "bottom_volume"          # 底部放量
    BOX_OSCILLATION = "box_oscillation"      # 箱体震荡
    BULL_TREND = "bull_trend"                # 默认多头趋势
    CHAN_THEORY = "chan_theory"              # 缠论
    MA_GOLDEN_CROSS = "ma_golden_cross"      # 均线金叉
    ONE_YANG_THREE_YIN = "one_yang_three_yin"  # 一阳夹三阴
    SHRINK_PULLBACK = "shrink_pullback"      # 缩量回踩
    VOLUME_BREAKOUT = "volume_breakout"      # 放量突破
    WAVE_THEORY = "wave_theory"              # 波浪理论


class StrategyInfo(BaseModel):
    id: str
    name: str
    name_en: str
    description: str
    priority: int
    market_state: str
    signals: list[str]


class StrategySignal(BaseModel):
    name: str
    value: str | float | bool
    description: str


class StrategyStockItem(BaseModel):
    symbol: str
    name: str
    exchange: str
    close: Optional[float] = None
    change_pct: Optional[float] = None
    turnover_rate: Optional[float] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    volume_ratio: Optional[float] = None
    trend_score: Optional[float] = None
    signals: list[StrategySignal] = Field(default_factory=list)
    match_reason: str
    score: float = Field(ge=0, le=100)


class StrategyQueryRequest(BaseModel):
    strategy_id: str
    trade_date: str
    limit: int = Field(default=20, ge=1, le=200)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class StrategyStats(BaseModel):
    total_count: int
    avg_trend_score: Optional[float] = None
    avg_change_pct: Optional[float] = None
    avg_turnover_rate: Optional[float] = None


class StrategyQueryData(BaseModel):
    strategy: StrategyInfo
    items: list[StrategyStockItem]
    total: int
    stats: StrategyStats


# ── 问股分析 ─────────────────────────────────────────────

class StockAnalyzeRequest(BaseModel):
    symbol: str
    trade_date: Optional[str] = None


class StrategyAnalysisResult(BaseModel):
    strategy_id: str
    strategy_name: str
    triggered: bool
    score: float = Field(ge=0, le=100)
    signals: list[StrategySignal] = Field(default_factory=list)
    match_reason: str
    priority: int


class StockAnalyzeData(BaseModel):
    symbol: str
    name: str
    exchange: str
    close: Optional[float] = None
    change_pct: Optional[float] = None
    turnover_rate: Optional[float] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    volume_ratio: Optional[float] = None
    trend_score: Optional[float] = None
    results: list[StrategyAnalysisResult]