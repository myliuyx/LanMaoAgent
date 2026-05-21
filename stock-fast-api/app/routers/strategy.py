from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.response import success_response
from app.schemas.strategy import (
    StrategyInfo,
    StrategyQueryRequest,
    StockAnalyzeRequest,
)
from app.services.strategy_service import StrategyService

router = APIRouter(prefix="/strategies", tags=["Strategies"])


@router.get("", summary="获取全部策略列表")
def list_strategies(db: Session = Depends(get_db)):
    service = StrategyService(db)
    data = service.list_strategies()
    return success_response(data)


@router.get("/{strategy_id}", summary="获取单个策略详情")
def get_strategy(strategy_id: str, db: Session = Depends(get_db)):
    service = StrategyService(db)
    try:
        data = service.get_strategy_info(strategy_id)
        return success_response(data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/query", summary="执行策略查询")
def query_strategy(
    req: StrategyQueryRequest,
    db: Session = Depends(get_db),
):
    service = StrategyService(db)
    try:
        data = service.query(req)
        return success_response(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze", summary="问股分析")
def analyze_stock(
    req: StockAnalyzeRequest,
    db: Session = Depends(get_db),
):
    """给定一只股票，用9种策略分别分析并返回结果。"""
    service = StrategyService(db)
    try:
        data = service.analyze(req)
        return success_response(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))