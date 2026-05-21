from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.response import success_response, error_response
from app.services.backfill_service import BackfillService
from app.schemas.backfill import BackfillRunRequest
import logging

router = APIRouter(prefix="/backfill", tags=["Backfill"])
logger = logging.getLogger("stock_api")


@router.post("/run", summary="触发补历史任务")
def run_backfill(
    background_tasks: BackgroundTasks,
    req: BackfillRunRequest,
    db: Session = Depends(get_db),
):
    service = BackfillService(db)
    result = service.run_backfill(
        symbol=req.symbol,
        data_type=req.data_type,
        start_date=req.start_date,
        end_date=req.end_date,
        force=req.force,
    )
    task_id = result.get("task_id")

    if task_id:
        def _run_backfill():
            from app.services.backfill_service import BackfillService
            from app.core.db import SessionLocal
            import traceback

            db_session = SessionLocal()
            try:
                svc = BackfillService(db_session)
                svc.execute_backfill(task_id, req.symbol, req.data_type, req.start_date, req.end_date, req.force)
            except Exception as e:
                logger.error(f"【补历史】task_id={task_id} 执行失败: {e}\n{traceback.format_exc()}")
                svc.mark_failed(task_id, str(e))
            finally:
                db_session.close()

        background_tasks.add_task(_run_backfill)

    return success_response(result)


@router.get("/status/{task_id}", summary="查询补历史状态")
def get_backfill_status(task_id: int, db: Session = Depends(get_db)):
    service = BackfillService(db)
    data = service.get_status(task_id)
    if data.get("status") == "NOT_FOUND":
        return error_response(code=4043, message="任务不存在")
    return success_response(data)
