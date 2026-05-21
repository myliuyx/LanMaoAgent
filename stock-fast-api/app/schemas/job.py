from typing import Optional
from pydantic import BaseModel
from app.schemas.common import PageData


class JobItem(BaseModel):
    id: int
    job_name: str
    biz_date: str
    status: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: Optional[int] = None
    rows_raw: Optional[int] = None
    rows_written: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None


class JobListData(PageData[JobItem]):
    pass


class RunJobRequest(BaseModel):
    job_name: str
    biz_date: str | None = None
    force: bool = False
