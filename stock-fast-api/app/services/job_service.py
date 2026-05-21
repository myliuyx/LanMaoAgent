from sqlalchemy.orm import Session
import datetime
import time
import logging
from app.repositories.job_repository import JobRepository

logger = logging.getLogger("stock_api")


class JobService:
    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAYS = [2, 4, 8]  # 指数退避：2秒、4秒、8秒

    def __init__(self, db: Session):
        self.db = db
        self.repo = JobRepository(db)

    def list_jobs(self, page: int, page_size: int, job_name: str | None = None, status: str | None = None, biz_date: str | None = None) -> dict:
        return self.repo.list_jobs(page=page, page_size=page_size, job_name=job_name, status=status, biz_date=biz_date)

    def get_job(self, job_id: int) -> dict | None:
        return self.repo.get_job(job_id)

    def get_logs(self, job_id: int, offset: int, limit: int) -> dict:
        return self.repo.get_logs(job_id, offset, limit)

    def run_job(self, job_name: str, biz_date: str | None, force: bool) -> dict:
        """兼容接口，内部调用 prepare_run_job + run_job_task"""
        task_id = self.prepare_run_job(job_name, biz_date, force).get("task_id")
        if task_id is not None:
            self.run_job_task(task_id, job_name, biz_date, force)
        return {"task_id": task_id, "job_name": job_name, "biz_date": biz_date}

    def prepare_run_job(self, job_name: str, biz_date: str | None, force: bool) -> dict:
        """创建任务记录，立即返回（不执行 ETL）"""
        job_id = self.init_job_run(job_name, biz_date)
        return {
            "task_id": job_id,
            "job_name": job_name,
            "biz_date": biz_date,
            "message": f"任务已创建，job_id={job_id}",
        }

    def run_job_task(self, task_id: int, job_name: str, biz_date: str | None, force: bool):
        """后台执行 ETL 任务（由 BackgroundTasks 调用），支持自动重试"""
        import os
        from app.jobs.sync_stock_daily import sync_stock_daily
        from app.jobs.etl_financial_indicator import main as financial_main
        from app.jobs.compute_factor import main as factor_main
        from app.jobs.build_selection_mart import main as selection_main

        self.repo.add_log(task_id, "INFO", f"开始执行 job_name={job_name}, biz_date={biz_date}, force={force}")

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                self._execute_job_logic(task_id, job_name, biz_date, force, sync_stock_daily, financial_main, factor_main, selection_main, os)
                return  # 成功执行，直接返回
            except Exception as e:
                last_error = e
                self.repo.add_log(task_id, "ERROR", f"任务执行失败（尝试 {attempt + 1}/{self.MAX_RETRIES}）: {e}")

                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAYS[attempt]
                    self.repo.add_log(task_id, "INFO", f"等待 {delay} 秒后重试...")
                    time.sleep(delay)
                else:
                    # 所有重试都失败
                    error_msg = f"任务执行失败，已重试 {self.MAX_RETRIES} 次。最后错误: {e}"
                    self.update_job_run(task_id, "FAILED", error_message=error_msg)
                    self.repo.add_log(task_id, "ERROR", f"任务彻底失败，已重试 {self.MAX_RETRIES} 次。错误: {e}")
                    self._send_alert(task_id, job_name, error_msg)

    def _execute_job_logic(self, task_id: int, job_name: str, biz_date: str | None, force: bool,
                           sync_stock_daily, financial_main, factor_main, selection_main, os):
        """执行任务的核心逻辑（无重试）"""
        import datetime

        if job_name.startswith("daily_kline"):
            trade_date = biz_date
            sync_stock_daily(force_restart=force, start_date=trade_date, end_date=trade_date)
            self.update_job_run(task_id, "COMPLETED", rows_written=0)
            self.repo.add_log(task_id, "INFO", "日线同步完成")

        elif job_name.startswith("financial"):
            if biz_date:
                year = int(biz_date[:4]) if len(biz_date) >= 4 else datetime.now().year
                os.environ['SYNC_YEAR'] = str(year)
                os.environ.pop('SYNC_START_YEAR', None)
                os.environ.pop('SYNC_END_YEAR', None)
            financial_main()
            self.update_job_run(task_id, "COMPLETED", rows_written=0)
            self.repo.add_log(task_id, "INFO", "财务指标同步完成")

        elif job_name.startswith("factor") or job_name.startswith("compute"):
            factor_main()
            self.update_job_run(task_id, "COMPLETED", rows_written=0)
            self.repo.add_log(task_id, "INFO", "技术因子计算完成")

        elif job_name.startswith("selection"):
            selection_main()
            self.update_job_run(task_id, "COMPLETED", rows_written=0)
            self.repo.add_log(task_id, "INFO", "选股宽表构建完成")

        elif job_name.startswith("cleanup"):
            from app.scheduler import run_cleanup_logs_job
            run_cleanup_logs_job(task_id, job_name, biz_date, force)

        else:
            self.repo.add_log(task_id, "WARN", f"未知的 job_name: {job_name}")
            self.update_job_run(task_id, "FAILED", error_message=f"未知任务类型: {job_name}")

    def _send_alert(self, task_id: int, job_name: str, error_message: str):
        """
        发送告警（目前仅记录日志，后续可扩展为 webhook/邮件/Slack 等）
        """
        logger.error(f"🚨 [ALERT] 任务 {job_name} (task_id={task_id}) 执行失败: {error_message}")
        # TODO: 扩展为 webhook 告警
        # self._send_webhook_alert(task_id, job_name, error_message)

    def cancel_job(self, job_id: int) -> bool:
        return self.repo.cancel_job(job_id)

    def init_job_run(self, job_name: str, biz_date: str | None = None) -> int:
        return self.repo.init_job_run(job_name, biz_date)

    def update_job_run(
        self,
        job_id: int,
        status: str,
        rows_raw: int | None = None,
        rows_written: int | None = None,
        error_message: str | None = None,
    ):
        self.repo.update_job_run(job_id, status, rows_raw, rows_written, error_message)

    def cancel_job(self, job_id: int) -> bool:
        return self.repo.cancel_job(job_id)

    def init_job_run(self, job_name: str, biz_date: str | None = None) -> int:
        return self.repo.init_job_run(job_name, biz_date)

    def update_job_run(
        self,
        job_id: int,
        status: str,
        rows_raw: int | None = None,
        rows_written: int | None = None,
        error_message: str | None = None,
    ):
        self.repo.update_job_run(job_id, status, rows_raw, rows_written, error_message)
