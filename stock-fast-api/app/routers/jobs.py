from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.response import success_response, error_response
from app.services.job_service import JobService
from app.schemas.job import RunJobRequest
import logging

logger = logging.getLogger("stock_api")

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", summary="获取任务列表")
def list_jobs(
    job_name: str | None = Query(None, description="任务名模糊搜索"),
    status: str | None = Query(None, description="PENDING / RUNNING / SUCCESS / FAILED / CANCELLED"),
    biz_date: str | None = Query(None, description="业务日期 YYYY-MM-DD"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    service = JobService(db)
    data = service.list_jobs(page=page, page_size=page_size, job_name=job_name, status=status, biz_date=biz_date)
    return success_response(data)


@router.post("/sync-trade-calendar", summary="手动触发交易日历同步")
def trigger_trade_calendar_sync(
    background_tasks: BackgroundTasks,
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD，不传则从年初"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD，不传则同步到今年年底+1年"),
    db: Session = Depends(get_db),
):
    import datetime

    if end_date is None:
        end_date = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
    if start_date is None:
        start_date = datetime.datetime.now().strftime('%Y-01-01')

    logger.info(f"【手动触发】交易日历同步 start={start_date} end={end_date}")

    service = JobService(db)
    job_id = service.init_job_run(f"trade_calendar_sync_{start_date}_{end_date}", end_date)

    def _run_sync():
        from app.services.job_service import JobService
        from app.core.db import engine
        from sqlalchemy import text
        import traceback

        try:
            from app.jobs.sync_trade_calendar import sync_trade_calendar
            count = sync_trade_calendar(start_date=start_date, end_date=end_date)
            service.update_job_run(job_id, "COMPLETED", rows_written=count)
            logger.info(f"【交易日历同步】job_id={job_id} 完成，写入 {count} 条")
        except Exception as e:
            service.update_job_run(job_id, "FAILED", error_message=str(e))
            logger.error(f"【交易日历同步】job_id={job_id} 失败: {e}\n{traceback.format_exc()}")

    background_tasks.add_task(_run_sync)
    return success_response({
        "status": "triggered",
        "job_id": job_id,
        "start_date": start_date,
        "end_date": end_date,
        "message": f"交易日历同步任务已触发，job_id={job_id}",
    })


@router.post("/sync-daily", summary="手动触发日线同步")
def trigger_daily_sync(
    background_tasks: BackgroundTasks,
    trade_date: str = Query(None, description="交易日期 YYYY-MM-DD，不传则用昨天"),
    force_restart: bool = Query(False, description="是否强制从头开始"),
):
    import datetime
    if trade_date is None:
        trade_date = datetime.datetime.now().strftime("%Y-%m-%d")

    logger.info(f"【手动触发】日线同步 trade_date={trade_date}, force={force_restart}")

    def _run_sync():
        from app.jobs.sync_stock_daily import sync_stock_daily
        sync_stock_daily(force_restart=force_restart, start_date=trade_date, end_date=trade_date)

    background_tasks.add_task(_run_sync)
    return success_response({
        "status": "triggered",
        "trade_date": trade_date,
        "force_restart": force_restart,
        "message": "日线同步任务已在后台触发，请关注日志查看进度",
    })


@router.post("/sync-financial", summary="手动触发财务指标同步")
def trigger_financial_sync(
    background_tasks: BackgroundTasks,
    year: int = Query(None, description="年份，如 2026"),
    quarter: int = Query(None, description="季度 1-4"),
    start_year: int = Query(None, description="起始年份，如 2021"),
    end_year: int = Query(None, description="结束年份，如 2026"),
    db: Session = Depends(get_db),
):
    import os
    import datetime

    # 默认同步当前季度
    if year is None or quarter is None:
        now = datetime.datetime.now()
        month = now.month
        if month <= 3:
            quarter = 1
        elif month <= 6:
            quarter = 2
        elif month <= 9:
            quarter = 3
        else:
            quarter = 4
        year = now.year

    # 构造 job_name
    if start_year is not None and end_year is not None:
        job_name = f"financial_indicator_sync_{start_year}_{end_year}"
    else:
        job_name = f"financial_indicator_sync_{year}Q{quarter}"

    logger.info(f"【手动触发】财务指标同步 job={job_name}")

    # 先创建 job 记录
    service = JobService(db)
    job_id = service.init_job_run(job_name, str(year))

    def _run_sync():
        from app.services.job_service import JobService
        from app.core.db import engine
        from app.jobs.etl_financial_indicator import main as financial_main
        import traceback

        # 设置环境变量控制同步范围
        if year is not None and quarter is not None:
            os.environ['SYNC_YEAR'] = str(year)
            os.environ['SYNC_QUARTER'] = str(quarter)
            os.environ.pop('SYNC_START_YEAR', None)
            os.environ.pop('SYNC_END_YEAR', None)
        elif start_year is not None and end_year is not None:
            os.environ['SYNC_START_YEAR'] = str(start_year)
            os.environ['SYNC_END_YEAR'] = str(end_year)
            os.environ.pop('SYNC_YEAR', None)
            os.environ.pop('SYNC_QUARTER', None)
        else:
            os.environ.pop('SYNC_YEAR', None)
            os.environ.pop('SYNC_QUARTER', None)
            os.environ.pop('SYNC_START_YEAR', None)
            os.environ.pop('SYNC_END_YEAR', None)

        try:
            financial_main()
            # 查询实际写入行数
            with engine.connect() as conn:
                from sqlalchemy import text
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM dwd_stock_financial_indicator
                    WHERE updated_at > (SELECT start_time FROM etl_job_run WHERE id = :job_id)
                """), {"job_id": job_id})
                rows_written = result.fetchone()[0]
            service.update_job_run(job_id, "COMPLETED", rows_written=rows_written)
            logger.info(f"【财务指标同步】job_id={job_id} 完成，写入 {rows_written} 条")
        except Exception as e:
            service.update_job_run(job_id, "FAILED", error_message=str(e))
            logger.error(f"【财务指标同步】job_id={job_id} 失败: {e}\\n{traceback.format_exc()}")

    background_tasks.add_task(_run_sync)
    return success_response({
        "status": "triggered",
        "job_id": job_id,
        "year": year,
        "quarter": quarter,
        "start_year": start_year,
        "end_year": end_year,
        "message": f"财务指标同步任务已触发，job_id={job_id}",
    })


@router.post("/sync-factor", summary="手动触发技术因子计算")
def trigger_factor_sync(
    background_tasks: BackgroundTasks,
    trade_date: str = Query(None, description="交易日期 YYYY-MM-DD，不传则计算最近5个交易日"),
    full: bool = Query(False, description="是否全量重算（最近2年）"),
):
    import datetime

    logger.info(f"【手动触发】技术因子计算 trade_date={trade_date}, full={full}")

    def _run_sync():
        from app.jobs.compute_factor import main as factor_main
        import sys
        sys.argv = ['compute_factor.py']
        if full:
            sys.argv.extend(['--full'])
        elif trade_date:
            sys.argv.extend(['--date', trade_date])
        else:
            # 默认最近5个交易日，不传参数即可
            pass
        factor_main()

    background_tasks.add_task(_run_sync)
    return success_response({
        "status": "triggered",
        "trade_date": trade_date,
        "full": full,
        "message": "技术因子计算任务已在后台触发，请关注日志查看进度",
    })


@router.post("/sync-selection", summary="手动触发选股宽表构建")
def trigger_selection_sync(
    background_tasks: BackgroundTasks,
    trade_date: str = Query(None, description="交易日期 YYYY-MM-DD，不传则构建最近5个交易日"),
    full: bool = Query(False, description="是否全量重算（最近2年）"),
):
    import datetime

    logger.info(f"【手动触发】选股宽表构建 trade_date={trade_date}, full={full}")

    def _run_sync():
        from app.jobs.build_selection_mart import main as selection_main
        import sys
        sys.argv = ['build_selection_mart.py']
        if full:
            sys.argv.extend(['--full'])
        elif trade_date:
            sys.argv.extend(['--date', trade_date])
        else:
            # 默认最近5个交易日
            pass
        selection_main()

    background_tasks.add_task(_run_sync)
    return success_response({
        "status": "triggered",
        "trade_date": trade_date,
        "full": full,
        "message": "选股宽表构建任务已在后台触发，请关注日志查看进度",
    })


@router.post("/sync-adjust-factor", summary="手动触发复权因子同步")
def trigger_adjust_factor_sync(
    background_tasks: BackgroundTasks,
    start_year: int = Query(2010, ge=2000, le=2030, description="起始年份，默认 2010"),
    end_year: int = Query(None, description="结束年份，不传则用今年"),
    db: Session = Depends(get_db),
):
    import datetime

    if end_year is None:
        end_year = datetime.datetime.now().year

    logger.info(f"【手动触发】复权因子同步 {start_year}-{end_year}")

    service = JobService(db)
    job_id = service.init_job_run(f"adjust_factor_sync_{start_year}_{end_year}", str(end_year))

    def _run_sync():
        from app.services.job_service import JobService
        from app.core.db import engine
        from sqlalchemy import text
        import os
        import traceback

        os.environ['SYNC_START_YEAR'] = str(start_year)
        os.environ['SYNC_END_YEAR'] = str(end_year)

        try:
            from app.jobs.sync_adjust_factor import main as adjust_factor_main
            adjust_factor_main()

            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM dwd_stock_adjust_factor
                    WHERE updated_at > (SELECT start_time FROM etl_job_run WHERE id = :job_id)
                """), {"job_id": job_id})
                rows_written = result.fetchone()[0]
            service.update_job_run(job_id, "COMPLETED", rows_written=rows_written)
            logger.info(f"【复权因子同步】job_id={job_id} 完成，写入 {rows_written} 条")
        except Exception as e:
            service.update_job_run(job_id, "FAILED", error_message=str(e))
            logger.error(f"【复权因子同步】job_id={job_id} 失败: {e}\n{traceback.format_exc()}")

    background_tasks.add_task(_run_sync)
    return success_response({
        "status": "triggered",
        "job_id": job_id,
        "start_year": start_year,
        "end_year": end_year,
        "message": f"复权因子同步任务已触发，job_id={job_id}",
    })


@router.post("/run", summary="手工触发任务")
def run_job(
    background_tasks: BackgroundTasks,
    req: RunJobRequest,
    db: Session = Depends(get_db),
):
    service = JobService(db)
    result = service.prepare_run_job(req.job_name, req.biz_date, req.force)
    task_id = result.get("task_id")

    if task_id is None:
        return success_response(result)

    def _run():
        from app.services.job_service import JobService
        from app.core.db import SessionLocal
        import traceback

        # 重新创建 session 执行
        db_session = SessionLocal()
        try:
            svc = JobService(db_session)
            svc.run_job_task(task_id, req.job_name, req.biz_date, req.force)
        except Exception as e:
            logger.error(f"【手动触发任务】job_id={task_id} 失败: {e}\n{traceback.format_exc()}")
        finally:
            db_session.close()

    background_tasks.add_task(_run)
    return success_response(result)


@router.get("/{job_id}", summary="获取任务详情")
def get_job_detail(job_id: int, db: Session = Depends(get_db)):
    service = JobService(db)
    data = service.get_job(job_id)
    if data is None:
        return error_response(code=4043, message="job not found")
    return success_response(data)


@router.get("/{job_id}/logs", summary="获取任务日志")
def get_job_logs(
    job_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    service = JobService(db)
    data = service.get_logs(job_id, offset, limit)
    return success_response(data)


@router.post("/{job_id}/cancel", summary="取消任务")
def cancel_job(job_id: int, db: Session = Depends(get_db)):
    service = JobService(db)
    success = service.cancel_job(job_id)
    return success_response({"cancelled": success})


@router.post("/sync-new-ipo-boards", summary="手动触发新股板块增量同步")
def trigger_new_ipo_boards_sync(
    background_tasks: BackgroundTasks,
    days: int = Query(default=7, ge=1, le=30, description="查询近N天新股，默认7天"),
    db: Session = Depends(get_db),
):
    """
    触发新股板块增量同步（基于 efinance）。
    查询近 N 天内上市的新股，获取其所属板块，写入 dwd_board_master + dwd_board_relation。
    """
    import datetime

    logger.info(f"【手动触发】新股板块增量同步（近 {days} 天）")

    service = JobService(db)
    job_id = service.init_job_run(f"new_ipo_board_sync_{days}days", datetime.datetime.now().strftime('%Y-%m-%d'))

    def _run():
        from app.services.job_service import JobService
        from app.core.db import SessionLocal
        import traceback

        db_session = SessionLocal()
        try:
            svc = JobService(db_session)
            from app.jobs.sync_new_ipo_boards import sync_new_ipo_boards
            result = sync_new_ipo_boards(days=days)
            svc.update_job_run(job_id, "COMPLETED", rows_written=result.get("boards", 0))
            logger.info(f"【新股板块增量同步】job_id={job_id} 完成: {result}")
        except Exception as e:
            svc.update_job_run(job_id, "FAILED", error_message=str(e))
            logger.error(f"【新股板块增量同步】job_id={job_id} 失败: {e}\n{traceback.format_exc()}")
        finally:
            db_session.close()

    background_tasks.add_task(_run)
    return success_response({
        "status": "triggered",
        "job_id": job_id,
        "days": days,
        "message": f"新股板块增量同步已触发，job_id={job_id}",
    })


@router.post("/sync-board-relation-full", summary="手动触发全量板块关系同步")
def trigger_board_relation_full_sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    触发全量板块关系同步（基于 efinance）。
    对 dwd_security_master 中所有 LISTED 股票重新获取板块数据。
    """
    import datetime

    logger.info("【手动触发】全量板块关系同步（efinance）")

    service = JobService(db)
    job_id = service.init_job_run("board_relation_full_sync", datetime.datetime.now().strftime('%Y-%m-%d'))

    def _run():
        from app.services.job_service import JobService
        from app.core.db import SessionLocal
        from sqlalchemy import text
        import traceback

        db_session = SessionLocal()
        try:
            svc = JobService(db_session)

            # 获取全量股票
            result = db_session.execute(text("SELECT symbol FROM dwd_security_master WHERE status = 'LISTED' ORDER BY symbol"))
            symbols = [row[0] for row in result.fetchall()]

            # 逐只同步（复用 BoardSyncService 逻辑）
            from app.services.board_sync_service import BoardSyncService
            success_count = 0
            fail_count = 0
            total_boards = 0

            for symbol in symbols:
                sync_svc = BoardSyncService(db_session)
                r = sync_svc.sync_stock(symbol)
                if r["success"]:
                    success_count += 1
                    total_boards += r.get("boards_synced", 0)
                else:
                    fail_count += 1
                import time
                time.sleep(0.2)

            svc.update_job_run(job_id, "COMPLETED", rows_written=total_boards)
            logger.info(f"【全量板块关系同步】job_id={job_id} 完成: {success_count} ok, {fail_count} fail, {total_boards} boards")
        except Exception as e:
            svc.update_job_run(job_id, "FAILED", error_message=str(e))
            logger.error(f"【全量板块关系同步】job_id={job_id} 失败: {e}\n{traceback.format_exc()}")
        finally:
            db_session.close()

    background_tasks.add_task(_run)
    return success_response({
        "status": "triggered",
        "job_id": job_id,
        "message": f"全量板块关系同步已触发，job_id={job_id}，请关注日志查看进度",
    })
