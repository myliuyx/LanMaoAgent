from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.response import success_response
from app.services.coverage_service import CoverageService

router = APIRouter(prefix="/coverage", tags=["Coverage"])


@router.get("", summary="获取覆盖列表")
def get_coverage_list(
    symbol: str | None = None,
    data_type: str | None = None,
    is_full_history: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    service = CoverageService(db)
    data = service.get_list(symbol=symbol, data_type=data_type, is_full_history=is_full_history, page=page, page_size=page_size)
    return success_response(data)


@router.get("/summary", summary="获取数据覆盖摘要")
def get_coverage_summary(db: Session = Depends(get_db)):
    service = CoverageService(db)
    data = service.get_summary()
    return success_response(data)


@router.get("/{symbol}", summary="获取单只股票覆盖详情")
def get_coverage_detail(symbol: str, db: Session = Depends(get_db)):
    service = CoverageService(db)
    data = service.get_detail(symbol)
    return success_response(data)
