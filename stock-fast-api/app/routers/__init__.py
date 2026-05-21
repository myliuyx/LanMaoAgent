"""FastAPI 路由注册入口"""
from app.routers import auth, dashboard, selection, stocks, jobs, coverage, boards, backfill, system

__all__ = [
    "auth",
    "dashboard",
    "selection",
    "stocks",
    "jobs",
    "coverage",
    "boards",
    "backfill",
    "system",
]
