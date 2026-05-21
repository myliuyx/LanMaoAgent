from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import io

from app.core.deps import get_db
from app.core.response import success_response
from app.schemas.selection import SelectionQueryRequest
from app.services.selection_service import SelectionService

router = APIRouter(prefix="/selection", tags=["Selection"])


@router.get("/dates", summary="获取可选交易日列表")
def get_selection_dates(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    service = SelectionService(db)
    data = service.get_dates(start_date, end_date, limit)
    return success_response(data)


@router.get("/industries", summary="获取可选行业列表")
def get_selection_industries(db: Session = Depends(get_db)):
    service = SelectionService(db)
    data = service.get_industries()
    return success_response(data)


@router.get("/top", summary="选股结果Top榜")
def get_selection_top(
    days: int = Query(default=5, ge=1, le=30, description="统计近N个交易日"),
    limit: int = Query(default=10, ge=1, le=50, description="返回Top N"),
    db: Session = Depends(get_db),
):
    service = SelectionService(db)
    data = service.get_selection_top(days=days, limit=limit)
    return success_response(data)


@router.post("/query", summary="查询选股结果")
def query_selection(
    req: SelectionQueryRequest,
    db: Session = Depends(get_db),
):
    service = SelectionService(db)
    data = service.query(req)
    return success_response(data)


@router.post("/export", summary="导出选股结果")
def export_selection(req: SelectionQueryRequest, db: Session = Depends(get_db)):
    service = SelectionService(db)
    data = service.query(req)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "symbol", "name", "exchange", "close", "change_pct",
        "turnover_rate", "market_value", "ma20", "ma60",
        "is_new_high_60d", "trend_score", "is_st",
        "roe", "revenue_yoy", "net_profit_yoy", "industry_l1"
    ])
    for item in data["list"]:
        writer.writerow([
            item.get("symbol", ""), item.get("name", ""), item.get("exchange", ""),
            item.get("close", ""), item.get("change_pct", ""),
            item.get("turnover_rate", ""), item.get("market_value", ""),
            item.get("ma20", ""), item.get("ma60", ""),
            item.get("is_new_high_60d", ""), item.get("trend_score", ""),
            item.get("is_st", ""), item.get("roe", ""),
            item.get("revenue_yoy", ""), item.get("net_profit_yoy", ""),
            item.get("industry_l1", ""),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=selection_{req.trade_date}.csv"},
    )
