"""System schemas - 系统配置相关请求/响应模型"""
from pydantic import BaseModel


class SystemMetaResponse(BaseModel):
    """系统配置摘要响应"""
    env: str
    version: str
    db_status: str
    latest_trade_date: str
    scheduler_status: str
