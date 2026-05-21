"""Board schemas - 板块相关请求/响应模型"""
from typing import Optional
from pydantic import BaseModel, Field


class BoardListRequest(BaseModel):
    """板块列表请求"""
    board_type: Optional[str] = Field(None, description="INDUSTRY / CONCEPT / INDEX / AREA")
    keyword: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class BoardItem(BaseModel):
    """板块列表项"""
    board_code: str
    board_name: str
    board_type: str
    member_count: Optional[int] = None
    is_active: bool = True


class BoardDetailResponse(BaseModel):
    """板块详情响应"""
    board_code: str
    board_name: str
    board_type: str
    parent_board_code: Optional[str] = None
    is_active: bool = True


class BoardMemberItem(BaseModel):
    """板块成分股项"""
    symbol: str
    name: str
    exchange: str
    close: Optional[float] = None
    change_pct: Optional[float] = None
    turnover_rate: Optional[float] = None
    market_value: Optional[float] = None
    trend_score: Optional[float] = None
    industry_l1: Optional[str] = None
