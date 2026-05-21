"""Backfill schemas - 补历史相关请求/响应模型"""
from typing import Optional
from pydantic import BaseModel


class BackfillRunRequest(BaseModel):
    """触发补历史请求"""
    symbol: str
    data_type: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    force: bool = False


class BackfillRunResponse(BaseModel):
    """触发补历史响应"""
    task_id: int
    job_name: str


class BackfillStatusResponse(BaseModel):
    """补历史状态响应"""
    task_id: int
    symbol: Optional[str] = None
    data_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str
    progress: Optional[int] = None
    rows_written: Optional[int] = None
    error_message: Optional[str] = None
    force: Optional[bool] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    message: Optional[str] = None
