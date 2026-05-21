from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.response import success_response
from app.schemas.dashboard import WatchlistAnalysisRequest
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", summary="获取首页摘要")
def get_dashboard_summary(db: Session = Depends(get_db)):
    service = DashboardService(db)
    data = service.get_summary()
    return success_response(data)


@router.get("/jobs", summary="获取最近任务")
def get_recent_jobs(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    data = service.get_recent_jobs(limit=limit)
    return success_response(data)


@router.get("/coverage", summary="获取数据覆盖摘要")
def get_dashboard_coverage(db: Session = Depends(get_db)):
    service = DashboardService(db)
    data = service.get_coverage_summary()
    return success_response(data)


@router.post("/watchlist-analysis", summary="自选股技术面分析")
def watchlist_analysis(
    req: WatchlistAnalysisRequest,
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    data = service.watchlist_analysis(req.symbols)
    return success_response(data)
