from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.deps import get_db
from app.core.response import success_response, error_response
from app.services.board_service import BoardService
from app.services.board_sync_service import BoardSyncService

router = APIRouter(prefix="/boards", tags=["Boards"])


@router.get("", summary="获取板块列表")
def list_boards(
    board_type: str | None = Query(None, description="INDUSTRY / CONCEPT / INDEX / AREA"),
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    service = BoardService(db)
    data = service.list_boards(board_type=board_type, keyword=keyword, page=page, page_size=page_size)
    return success_response(data)


@router.get("/{board_code}", summary="获取板块详情")
def get_board(board_code: str, db: Session = Depends(get_db)):
    service = BoardService(db)
    data = service.get_board(board_code)
    if data is None:
        return error_response(code=4042, message="board not found")
    return success_response(data)


@router.get("/{board_code}/members", summary="获取板块成分股")
def get_board_members(
    board_code: str,
    trade_date: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    sort_by: str = Query(default="change_pct"),
    sort_order: str = Query(default="desc"),
    db: Session = Depends(get_db),
):
    service = BoardService(db)
    data = service.get_members(board_code, trade_date=trade_date, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order)
    return success_response(data)


class SyncRequest(BaseModel):
    """同步请求"""
    symbols: list[str]
    trade_date: str | None = None


@router.post("/sync", summary="同步单只股票板块数据")
def sync_board(symbol: str, db: Session = Depends(get_db)):
    """
    从 efinance 抓取单只股票的所属板块，写入 dwd_board_master + dwd_board_relation。
    """
    service = BoardSyncService(db)
    result = service.sync_stock(symbol)
    if not result["success"]:
        return error_response(code=5001, message=f"同步失败: {result['error']}")
    return success_response(result)


@router.post("/sync/batch", summary="批量同步股票板块数据")
def sync_boards_batch(req: SyncRequest, db: Session = Depends(get_db)):
    """
    批量同步多只股票的板块数据。
    body: {"symbols": ["600519", "000858"], "trade_date": "2026-05-03"}
    """
    from datetime import date
    trade_date = None
    if req.trade_date:
        trade_date = date.fromisoformat(req.trade_date)

    service = BoardSyncService(db)
    results = service.batch_sync(req.symbols, trade_date)
    return success_response({"results": results})
