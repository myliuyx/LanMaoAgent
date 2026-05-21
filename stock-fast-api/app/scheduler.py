"""
定时任务调度器
==============
支持在 FastAPI 启动时自动启动，关闭时自动清理
"""
from datetime import datetime, timedelta
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.jobs.sync_stock_daily import sync_stock_daily
from app.jobs.sync_security_master import main as sync_security_master_main
from app.jobs.sync_board import sync_board as sync_board_main
from app.jobs.sync_board_relation import sync_board_relation as sync_board_relation_main
from app.jobs.sync_new_ipo_boards import sync_new_ipo_boards

logger = logging.getLogger("stock_api.scheduler")

LOG_DIR = os.environ.get("SYNC_LOG_DIR", "/app/logs")
LOG_KEEP_DAYS = 3


def is_trade_day() -> bool:
    """检查今天是否是交易日"""
    from app.core.db import engine
    from sqlalchemy import text

    today = datetime.now().strftime('%Y-%m-%d')
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT is_open FROM dwd_trade_calendar WHERE trade_date = :today AND exchange = 'SH'"),
                {"today": today}
            )
            row = result.fetchone()
            if row:
                return row[0] is True
            return False
    except Exception as e:
        logger.warning(f"检查交易日失败: {e}")
        return False


def cleanup_old_logs():
    """清理超过 3 天的日志文件"""
    if not os.path.exists(LOG_DIR):
        return

    # 解析 LOG_DIR 的真实路径，防止符号链接路径穿越
    log_dir_real = os.path.realpath(LOG_DIR)
    cutoff = datetime.now() - timedelta(days=LOG_KEEP_DAYS)
    removed = 0
    for fname in os.listdir(LOG_DIR):
        if not fname.startswith("sync_stock_daily_") or not fname.endswith(".log"):
            continue
        fpath = os.path.join(LOG_DIR, fname)
        # 安全检查：确保真实路径在 LOG_DIR 内
        fpath_real = os.path.realpath(fpath)
        if not fpath_real.startswith(log_dir_real + os.sep):
            logger.warning(f"跳过路径外的文件: {fpath}")
            continue
        if not os.path.isfile(fpath_real):
            continue
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath_real))
        if mtime < cutoff:
            os.remove(fpath_real)
            removed += 1
    if removed:
        logger.info(f"🗑️ 已清理 {removed} 个过期日志文件（保留最近 {LOG_KEEP_DAYS} 天））")


def run_cleanup_logs_job(task_id: int, job_name: str, biz_date: str | None, force: bool):
    """供手动触发器调用的日志清理包装函数"""
    logger.info(f"【手动触发】日志清理任务开始")
    try:
        cleanup_old_logs()
        logger.info(f"【手动触发】日志清理任务完成")
    except Exception as e:
        logger.error(f"❌ 日志清理任务失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def run_daily_sync():
    """包装函数：执行日线同步任务"""
    from app.core.db import engine
    from sqlalchemy import text

    logger.info("=" * 60)
    logger.info(f"【定时任务】日线行情同步开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 检查是否为交易日
    if not is_trade_day():
        logger.info("⏭️ 今天非交易日，跳过日线同步")
        return

    try:
        # 验证数据库连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("📊 数据库连接正常")
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return

    try:
        sync_stock_daily(force_restart=False, start_date=None, end_date=None)
        logger.info(f"【定时任务】日线行情同步完成 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        logger.error(f"❌ 日线同步失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


def run_factor_compute():
    """包装函数：执行技术因子计算任务"""
    from app.jobs.compute_factor import main as factor_main
    import sys

    logger.info("=" * 60)
    logger.info(f"【定时任务】技术因子计算开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 检查是否为交易日
    if not is_trade_day():
        logger.info("⏭️ 今天非交易日，跳过技术因子计算")
        return

    try:
        sys.argv = ['compute_factor.py']
        factor_main()
        logger.info(f"【定时任务】技术因子计算完成 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        logger.error(f"❌ 技术因子计算失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


def run_selection_mart():
    """包装函数：执行选股宽表构建任务"""
    from app.jobs.build_selection_mart import main as selection_main
    import sys

    logger.info("=" * 60)
    logger.info(f"【定时任务】选股宽表构建开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 检查是否为交易日
    if not is_trade_day():
        logger.info("⏭️ 今天非交易日，跳过选股宽表构建")
        return

    try:
        sys.argv = ['build_selection_mart.py']
        selection_main()
        logger.info(f"【定时任务】选股宽表构建完成 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        logger.error(f"❌ 选股宽表构建失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


def run_security_master_sync():
    """包装函数：执行股票主数据同步任务"""
    logger.info("=" * 60)
    logger.info(f"【定时任务】股票主数据同步开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        sync_security_master_main()
        logger.info(f"【定时任务】股票主数据同步完成 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        logger.error(f"❌ 股票主数据同步失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


def run_board_sync():
    """包装函数：执行板块主数据同步任务"""
    logger.info("=" * 60)
    logger.info(f"【定时任务】板块主数据同步开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        sync_board_main()
        logger.info(f"【定时任务】板块主数据同步完成 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        logger.error(f"❌ 板块主数据同步失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


def run_board_relation_sync():
    """包装函数：执行股票-板块关系同步任务"""
    logger.info("=" * 60)
    logger.info(f"【定时任务】股票-板块关系同步开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        sync_board_relation_main()
        logger.info(f"【定时任务】股票-板块关系同步完成 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        logger.error(f"❌ 股票-板块关系同步失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


def run_new_ipo_board_sync():
    """包装函数：执行新股板块增量同步任务（周一至周五 22:00）"""
    logger.info("=" * 60)
    logger.info(f"【定时任务】新股板块增量同步开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        sync_new_ipo_boards(days=7)
        logger.info(f"【定时任务】新股板块增量同步完成 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        logger.error(f"❌ 新股板块增量同步失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


def create_scheduler() -> AsyncIOScheduler:
    """创建并配置调度器（使用北京时间）"""
    scheduler = AsyncIOScheduler(timezone='Asia/Shanghai')

    # 每周一至周五 18:00 执行股票主数据同步（北京时间，盘前）
    scheduler.add_job(
        func=run_security_master_sync,
        trigger=CronTrigger(hour=18, minute=0, day_of_week="0-4", timezone='Asia/Shanghai'),
        id="security_master_sync",
        name="股票主数据同步",
        replace_existing=True,
        misfire_grace_time=60 * 60,
    )

    # 板块主数据同步已移除（可手动触发 /api/v1/jobs/board-sync）
    # 股票-板块关系同步已移除（可手动触发 /api/v1/jobs/board-relation-sync）

    # 每周一至周五 22:00 新股板块增量同步（交易日结束后）
    scheduler.add_job(
        func=run_new_ipo_board_sync,
        trigger=CronTrigger(hour=22, minute=0, day_of_week="0-4", timezone='Asia/Shanghai'),
        id="new_ipo_board_sync",
        name="新股板块增量同步",
        replace_existing=True,
        misfire_grace_time=60 * 60,
    )

    # 每周一至周五 19:00 执行日线数据同步（北京时间）
    scheduler.add_job(
        func=run_daily_sync,
        trigger=CronTrigger(hour=19, minute=0, day_of_week="0-4", timezone='Asia/Shanghai'),
        id="daily_stock_sync",
        name="日线行情同步",
        replace_existing=True,
        misfire_grace_time=60 * 60,  # 允许1小时内补执行
    )

    # 每周一至周五 20:30 执行技术因子计算（日线同步完成后）
    scheduler.add_job(
        func=run_factor_compute,
        trigger=CronTrigger(hour=20, minute=30, day_of_week="0-4", timezone='Asia/Shanghai'),
        id="factor_compute",
        name="技术因子计算",
        replace_existing=True,
        misfire_grace_time=60 * 60,
    )

    # 每周一至周五 21:30 执行选股宽表构建（因子计算完成后）
    scheduler.add_job(
        func=run_selection_mart,
        trigger=CronTrigger(hour=21, minute=30, day_of_week="0-4", timezone='Asia/Shanghai'),
        id="selection_mart",
        name="选股宽表构建",
        replace_existing=True,
        misfire_grace_time=60 * 60,
    )

    # 每天 00:05 清理过期日志
    scheduler.add_job(
        func=cleanup_old_logs,
        trigger=CronTrigger(hour=0, minute=5, timezone='Asia/Shanghai'),
        id="cleanup_logs",
        name="日志清理",
        replace_existing=True,
    )

    logger.info("✅ 定时任务已注册: 股票主数据同步 (周一至周五 18:00) + 日线同步 (周一至周五 19:00) + 因子计算 (周一至周五 20:30) + 选股宽表 (周一至周五 21:30) + 日志清理 (每天 00:05 北京时间) + 新股板块同步 (周一至周五 22:00)")
    return scheduler
