from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.core.exceptions import BizException
from app.utils.validation import validate_symbol

logger = logging.getLogger("stock_api")


class BackfillRepository:
    def __init__(self, db: Session):
        self.db = db

    def run_backfill(
        self,
        symbol: str,
        data_type: str,
        start_date: str | None,
        end_date: str | None,
        force: bool,
    ) -> dict:
        """触发补历史数据任务，写入 etl_backfill_task"""
        symbol = validate_symbol(symbol)
        if not symbol:
            raise BizException(code=4003, message="symbol 格式无效")

        valid_data_types = {"DAILY", "FINANCE", "FACTOR", "ADJUST_FACTOR"}
        if data_type.upper() not in valid_data_types:
            raise BizException(
                code=4005,
                message=f"不支持的 data_type: {data_type}，允许: {', '.join(sorted(valid_data_types))}",
            )

        # 检查股票是否存在
        exists = self.db.execute(
            text("SELECT 1 FROM dwd_security_master WHERE symbol = :symbol"),
            {"symbol": symbol},
        ).fetchone()
        if not exists:
            raise BizException(code=4041, message="stock not found")

        # 检查日期范围
        if start_date and end_date:
            if start_date > end_date:
                raise BizException(code=4006, message="start_date 不能大于 end_date")

        # 写入 etl_backfill_task
        result = self.db.execute(
            text("""
                INSERT INTO etl_backfill_task (symbol, data_type, start_date, end_date, status, force, created_at, updated_at)
                VALUES (:symbol, :data_type, :start_date, :end_date, 'PENDING', :force, NOW(), NOW())
                RETURNING id
            """),
            {
                "symbol": symbol,
                "data_type": data_type.upper(),
                "start_date": start_date,
                "end_date": end_date,
                "force": force,
            },
        )
        self.db.commit()
        task_id = result.fetchone()[0]

        logger.info(f"【补历史任务】创建成功 task_id={task_id}, symbol={symbol}, data_type={data_type}")

        return {
            "task_id": task_id,
            "job_name": f"{symbol} {data_type.upper()} 补数",
        }

    def get_status(self, task_id: int) -> dict:
        """查询补历史任务状态"""
        result = self.db.execute(
            text("""
                SELECT id, symbol, data_type, start_date, end_date, status, progress,
                       rows_written, error_message, force, created_at, updated_at
                FROM etl_backfill_task
                WHERE id = :task_id
            """),
            {"task_id": task_id},
        )
        row = result.fetchone()
        if not row:
            return {
                "task_id": task_id,
                "job_name": None,
                "status": "NOT_FOUND",
                "progress": None,
                "message": "任务不存在",
            }

        m = row._mapping
        return {
            "task_id": m["id"],
            "symbol": m["symbol"],
            "data_type": m["data_type"],
            "start_date": str(m["start_date"]) if m["start_date"] else None,
            "end_date": str(m["end_date"]) if m["end_date"] else None,
            "status": m["status"],
            "progress": m["progress"],
            "rows_written": m["rows_written"],
            "error_message": m["error_message"],
            "force": m["force"],
            "created_at": m["created_at"].isoformat() if m["created_at"] else None,
            "updated_at": m["updated_at"].isoformat() if m["updated_at"] else None,
        }

    def update_status(self, task_id: int, status: str, progress: int | None = None,
                      rows_written: int | None = None, error_message: str | None = None):
        """更新任务状态"""
        updates = ["status = :status", "updated_at = NOW()"]
        params = {"task_id": task_id, "status": status}
        if progress is not None:
            updates.append("progress = :progress")
            params["progress"] = progress
        if rows_written is not None:
            updates.append("rows_written = :rows_written")
            params["rows_written"] = rows_written
        if error_message is not None:
            updates.append("error_message = :error_message")
            params["error_message"] = error_message

        self.db.execute(
            text(f"UPDATE etl_backfill_task SET {', '.join(updates)} WHERE id = :task_id"),
            params,
        )
        self.db.commit()