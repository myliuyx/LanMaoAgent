from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.response import success_response
from app.services.stock_service import StockService

router = APIRouter(prefix="/stocks", tags=["Stocks"])


@router.get("/search", summary="搜索股票")
def search_stocks(
    keyword: str = Query(..., min_length=1),
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    service = StockService(db)
    data = service.search(keyword, limit)
    return success_response(data)


@router.get("/{symbol}/profile", summary="获取股票基础信息")
def get_stock_profile(symbol: str, db: Session = Depends(get_db)):
    service = StockService(db)
    data = service.get_profile(symbol)
    return success_response(data)


@router.get("/{symbol}/daily", summary="获取股票日线行情")
def get_stock_daily(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(default=120, ge=1, le=730),
    adjust: str = Query(default="qfq"),
    db: Session = Depends(get_db),
):
    service = StockService(db)
    data = service.get_daily(symbol, start_date, end_date, limit, adjust)
    return success_response(data)


@router.get("/{symbol}/factors", summary="获取股票技术因子")
def get_stock_factors(
    symbol: str,
    trade_date: str | None = None,
    limit: int = Query(default=60, ge=1, le=365),
    db: Session = Depends(get_db),
):
    service = StockService(db)
    data = service.get_factors(symbol, trade_date, limit)
    return success_response(data)


@router.get("/{symbol}/finance", summary="获取股票财务指标")
def get_stock_finance(
    symbol: str,
    limit: int = Query(default=8, ge=1, le=40),
    db: Session = Depends(get_db),
):
    service = StockService(db)
    data = service.get_finance(symbol, limit)
    return success_response(data)


@router.get("/{symbol}/adjust-factor", summary="获取股票复权因子")
def get_stock_adjust_factor(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    service = StockService(db)
    data = service.get_adjust_factors(symbol, start_date, end_date, limit)
    return success_response(data)


@router.get("/{symbol}/boards", summary="获取股票所属板块")
def get_stock_boards(symbol: str, db: Session = Depends(get_db)):
    service = StockService(db)
    data = service.get_boards(symbol)
    return success_response(data)


# 注意：/stocks/{symbol}/coverage 已移除（etl_data_coverage 为空）。
# 数据覆盖详情请使用 /coverage/{symbol} 接口。


@router.get("/{symbol}/latest", summary="获取股票最新摘要")
def get_stock_latest(symbol: str, db: Session = Depends(get_db)):
    service = StockService(db)
    data = service.get_latest(symbol)
    return success_response(data)
