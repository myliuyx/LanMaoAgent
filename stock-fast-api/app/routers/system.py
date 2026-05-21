from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.deps import get_db
from app.core.response import success_response

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/meta", summary="获取系统配置摘要")
def get_meta(db: Session = Depends(get_db)):
    """
    返回系统元信息：
    - env: 运行环境
    - version: API 版本（从配置）
    - db_status: 数据库连接状态
    - latest_trade_date: 最新交易日（从 dwd_trade_calendar 查）
    - latest_daily_date: 最新日线数据日期（从 dwd_stock_daily 查）
    - scheduler_status: ETL 调度状态（从 etl_job_run 查最新任务状态）
    """
    try:
        # 最新交易日
        r = db.execute(
            text("""
                SELECT MAX(trade_date)
                FROM dwd_trade_calendar
                WHERE is_open = true AND trade_date <= CURRENT_DATE
            """)
        )
        latest_trade_date = str(r.fetchone()[0] or "N/A")

        # 最新日线数据日期
        r = db.execute(text("SELECT MAX(trade_date) FROM dwd_stock_daily"))
        latest_daily_date = str(r.fetchone()[0] or "N/A")

        # 最新 ETL 任务状态
        r = db.execute(
            text("""
                SELECT status
                FROM etl_job_run
                ORDER BY created_at DESC
                LIMIT 1
            """)
        )
        latest_job_row = r.fetchone()
        latest_job_status = latest_job_row[0] if latest_job_row else "N/A"

        # scheduler_status 逻辑：
        # - 有 RUNNING 任务 → RUNNING
        # - 有 24h 内失败任务 → ERROR
        # - 否则 → IDLE
        r = db.execute(
            text("""
                SELECT COUNT(*)
                FROM etl_job_run
                WHERE status = 'RUNNING'
            """)
        )
        running_count = r.fetchone()[0] or 0

        if running_count > 0:
            scheduler_status = "RUNNING"
        else:
            r = db.execute(
                text("""
                    SELECT COUNT(*)
                    FROM etl_job_run
                    WHERE status IN ('FAILED', 'PARTIAL')
                      AND created_at >= NOW() - INTERVAL '24 hours'
                """)
            )
            failed_recent = r.fetchone()[0] or 0
            scheduler_status = "ERROR" if failed_recent > 0 else "IDLE"

        # 数据库连接测试
        db.execute(text("SELECT 1"))
        db_status = "OK"

    except Exception as e:
        latest_trade_date = "ERROR"
        latest_daily_date = "ERROR"
        scheduler_status = "ERROR"
        latest_job_status = "ERROR"
        db_status = f"ERROR: {str(e)[:50]}"

    from app.core.config import settings
    return success_response({
        "env": "prod",
        "version": settings.APP_VERSION,
        "db_status": db_status,
        "latest_trade_date": latest_trade_date,
        "latest_daily_date": latest_daily_date,
        "scheduler_status": scheduler_status,
        "latest_etl_status": latest_job_status,
    })
