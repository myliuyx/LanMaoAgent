from sqlalchemy.orm import Session
from app.repositories.backfill_repository import BackfillRepository
import logging
import os

logger = logging.getLogger("stock_api")


class BackfillService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BackfillRepository(db)

    def run_backfill(self, symbol: str, data_type: str, start_date: str | None, end_date: str | None, force: bool) -> dict:
        return self.repo.run_backfill(symbol, data_type, start_date, end_date, force)

    def get_status(self, task_id: int) -> dict:
        result = self.repo.get_status(task_id)
        if result.get("status") == "NOT_FOUND":
            result["message"] = "任务不存在"
        return result

    def execute_backfill(self, task_id: int, symbol: str, data_type: str, start_date: str | None, end_date: str | None, force: bool):
        """后台执行补历史任务"""

        self.repo.update_status(task_id, "RUNNING", progress=0)
        logger.info(f"【补历史】task_id={task_id} 开始执行 symbol={symbol} data_type={data_type}")

        try:
            if data_type.upper() == "DAILY":
                self._sync_daily_backfill(task_id, symbol, start_date, end_date, force)
            elif data_type.upper() == "FINANCE":
                self._sync_financial_backfill(task_id, symbol, start_date, end_date)
            elif data_type.upper() == "FACTOR":
                self._sync_factor_backfill(task_id, symbol, start_date, end_date)
            elif data_type.upper() == "ADJUST_FACTOR":
                self._sync_adjust_factor_backfill(task_id, symbol, start_date, end_date)
            else:
                raise ValueError(f"不支持的 data_type: {data_type}")

            self.repo.update_status(task_id, "SUCCESS", progress=100, rows_written=0)
            logger.info(f"【补历史】task_id={task_id} 执行完成")

        except Exception as e:
            logger.error(f"【补历史】task_id={task_id} 执行失败: {e}")
            self.repo.update_status(task_id, "FAILED", error_message=str(e))

    def _sync_daily_backfill(self, task_id: int, symbol: str, start_date: str | None, end_date: str | None, force: bool):
        from app.jobs.sync_stock_daily import sync_stock_daily
        self.repo.update_status(task_id, "RUNNING", progress=10)
        sync_stock_daily(
            force_restart=force,
            start_date=start_date,
            end_date=end_date,
            target_symbol=symbol,
        )
        self.repo.update_status(task_id, "RUNNING", progress=90)

    def _sync_financial_backfill(self, task_id: int, symbol: str, start_date: str | None, end_date: str | None):
        from app.jobs.etl_financial_indicator import main as financial_main
        self.repo.update_status(task_id, "RUNNING", progress=10)

        # 备份并设置环境变量（临时修改全局状态，存在竞态风险，并发部署时需注意）
        old_start = os.environ.get('SYNC_START_YEAR')
        old_end = os.environ.get('SYNC_END_YEAR')
        try:
            if start_date and len(start_date) >= 4:
                try:
                    year = int(start_date[:4])
                    os.environ['SYNC_START_YEAR'] = str(year)
                except ValueError:
                    pass
            if end_date and len(end_date) >= 4:
                try:
                    year = int(end_date[:4])
                    os.environ['SYNC_END_YEAR'] = str(year)
                except ValueError:
                    pass
            financial_main()
        finally:
            # 恢复原值
            if old_start is not None:
                os.environ['SYNC_START_YEAR'] = old_start
            elif 'SYNC_START_YEAR' in os.environ:
                del os.environ['SYNC_START_YEAR']
            if old_end is not None:
                os.environ['SYNC_END_YEAR'] = old_end
            elif 'SYNC_END_YEAR' in os.environ:
                del os.environ['SYNC_END_YEAR']

        self.repo.update_status(task_id, "RUNNING", progress=90)

    def _sync_factor_backfill(self, task_id: int, symbol: str, start_date: str | None, end_date: str | None):
        from app.jobs.compute_factor import main as factor_main
        self.repo.update_status(task_id, "RUNNING", progress=10)
        import sys
        sys.argv = ['compute_factor.py']
        if start_date:
            sys.argv.extend(['--start-date', start_date])
        if end_date:
            sys.argv.extend(['--end-date', end_date])
        factor_main()
        self.repo.update_status(task_id, "RUNNING", progress=90)

    def _sync_adjust_factor_backfill(self, task_id: int, symbol: str, start_date: str | None, end_date: str | None):
        self.repo.update_status(task_id, "RUNNING", progress=10)
        raise NotImplementedError("ADJUST_FACTOR 同步暂未实现")

    def mark_failed(self, task_id: int, error_message: str):
        self.repo.update_status(task_id, "FAILED", error_message=error_message)
