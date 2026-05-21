"""Pydantic Schema / DTO 模型统一导出"""
from app.schemas.common import ApiResponse, PageData
from app.schemas.auth import LoginRequest, LoginResponse, UserInfo, VerifyResponse
from app.schemas.dashboard import (
    DashboardSummaryData,
    WatchlistAnalysisRequest,
    WatchlistStockItem,
    WatchlistSummary,
    WatchlistAnalysisData,
)
from app.schemas.selection import (
    SelectionFilters,
    SelectionQueryRequest,
    SelectionItem,
    SelectionQueryData,
    SelectionTopItem,
)
from app.schemas.stock import StockProfileData, StockLatestData, AdjustFactorItem
from app.schemas.job import JobItem, JobListData, RunJobRequest
from app.schemas.coverage import CoverageSummaryData
from app.schemas.board import (
    BoardListRequest,
    BoardItem,
    BoardDetailResponse,
    BoardMemberItem,
)
from app.schemas.backfill import BackfillRunRequest, BackfillStatusResponse
from app.schemas.system import SystemMetaResponse

__all__ = [
    # common
    "ApiResponse",
    "PageData",
    # auth
    "LoginRequest",
    "LoginResponse",
    "UserInfo",
    "VerifyResponse",
    # dashboard
    "DashboardSummaryData",
    "WatchlistAnalysisRequest",
    "WatchlistStockItem",
    "WatchlistSummary",
    "WatchlistAnalysisData",
    # selection
    "SelectionFilters",
    "SelectionQueryRequest",
    "SelectionItem",
    "SelectionQueryData",
    "SelectionTopItem",
    # stock
    "StockProfileData",
    "StockLatestData",
    "AdjustFactorItem",
    # job
    "JobItem",
    "JobListData",
    "RunJobRequest",
    # coverage
    "CoverageSummaryData",
    # board
    "BoardListRequest",
    "BoardItem",
    "BoardDetailResponse",
    "BoardMemberItem",
    # backfill
    "BackfillRunRequest",
    "BackfillStatusResponse",
    # system
    "SystemMetaResponse",
]
