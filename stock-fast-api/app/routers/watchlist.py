from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.response import success_response
from app.schemas.watchlist import (
    WatchlistQuery,
    WatchlistAddRequest,
)
from app.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


def get_watchlist_service(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> WatchlistService:
    """创建带有当前用户上下文的 WatchlistService"""
    return WatchlistService(db, user_id=str(current_user["id"]))


@router.get("", summary="获取自选股列表")
def get_watchlist(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    service: WatchlistService = Depends(get_watchlist_service),
):
    data = service.get_watchlist(page, page_size)
    return success_response(data)


@router.post("", summary="添加股票到自选")
def add_watchlist(
    req: WatchlistAddRequest,
    service: WatchlistService = Depends(get_watchlist_service),
):
    data = service.add_stock(req.symbol)
    return success_response(data, message="添加成功")


@router.delete("/{symbol}", summary="删除自选股")
def delete_watchlist(
    symbol: str,
    service: WatchlistService = Depends(get_watchlist_service),
):
    service.remove_stock(symbol)
    return success_response(message="删除成功")


@router.get("/check/{symbol}", summary="检查股票是否在自选列表中")
def check_watchlist(
    symbol: str,
    service: WatchlistService = Depends(get_watchlist_service),
):
    data = service.check_stock(symbol)
    return success_response(data)
