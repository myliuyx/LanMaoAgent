from sqlalchemy.orm import Session
from sqlalchemy import text

from app.utils.pagination import paginate


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_jobs(
        self,
        page: int,
        page_size: int,
        job_name: str | None = None,
        status: str | None = None,
        biz_date: str | None = None,
    ) -> dict:
        """
        从 etl_job_run 查询 ETL 任务列表。
        支持按任务名模糊搜索、状态过滤、业务日期过滤。
        """
        sql = """
            SELECT id, job_name, biz_date, status,
                   start_time, end_time, duration_ms,
                   rows_raw, rows_written, error_message,
                   created_at
            FROM etl_job_run
            WHERE 1=1
        """
        params: dict = {}
        if job_name:
            sql += " AND job_name LIKE :job_name"
            params["job_name"] = f"%{job_name}%"
        if status:
            sql += " AND status = :status"
            params["status"] = status.upper()
        if biz_date:
            sql += " AND biz_date = :biz_date"
            params["biz_date"] = biz_date

        sql += " ORDER BY created_at DESC"

        # COUNT 查询（用于分页总数）
        count_sql = f"SELECT COUNT(*) FROM ({sql}) AS subq"
        total = self.db.execute(text(count_sql), params).fetchone()[0]

        # LIMIT/OFFSET 分页
        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size
        sql += " LIMIT :limit OFFSET :offset"

        result = self.db.execute(text(sql), params)
        rows = result.fetchall()

        items = [
            {
                "id": row._mapping["id"],
                "job_name": row._mapping["job_name"],
                "biz_date": str(row._mapping["biz_date"]) if row._mapping["biz_date"] else None,
                "status": row._mapping["status"],
                "start_time": row._mapping["start_time"].isoformat() if row._mapping["start_time"] else None,
                "end_time": row._mapping["end_time"].isoformat() if row._mapping["end_time"] else None,
                "duration_ms": row._mapping["duration_ms"],
                "rows_raw": row._mapping["rows_raw"],
                "rows_written": row._mapping["rows_written"],
                "error_message": row._mapping["error_message"],
                "created_at": row._mapping["created_at"].isoformat() if row._mapping["created_at"] else None,
            }
            for row in rows
        ]

        return {
            "list": items,
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    def get_job(self, job_id: int) -> dict | None:
        """根据 job_id 查询单条任务记录"""
        result = self.db.execute(
            text("""
                SELECT id, job_name, biz_date, status,
                       start_time, end_time, duration_ms,
                       rows_raw, rows_written, error_message,
                       created_at
                FROM etl_job_run
                WHERE id = :job_id
            """),
            {"job_id": job_id},
        )
        row = result.fetchone()
        if not row:
            return None

        m = row._mapping
        return {
            "id": m["id"],
            "job_name": m["job_name"],
            "biz_date": str(m["biz_date"]) if m["biz_date"] else None,
            "status": m["status"],
            "start_time": m["start_time"].isoformat() if m["start_time"] else None,
            "end_time": m["end_time"].isoformat() if m["end_time"] else None,
            "duration_ms": m["duration_ms"],
            "rows_raw": m["rows_raw"],
            "rows_written": m["rows_written"],
            "error_message": m["error_message"],
            "created_at": m["created_at"].isoformat() if m["created_at"] else None,
        }

    def get_logs(self, job_id: int, offset: int, limit: int) -> dict:
        """返回任务日志，从 etl_job_run_log 查询"""
        # 先检查任务是否存在
        job = self.get_job(job_id)
        if not job:
            return {"logs": [], "total": 0, "offset": offset, "limit": limit}

        # 查询日志条数
        count_result = self.db.execute(
            text("SELECT COUNT(*) FROM etl_job_run_log WHERE job_id = :job_id"),
            {"job_id": job_id},
        )
        total = count_result.fetchone()[0]

        # 查询日志列表
        result = self.db.execute(
            text("""
                SELECT level, message, created_at
                FROM etl_job_run_log
                WHERE job_id = :job_id
                ORDER BY created_at ASC
                OFFSET :offset LIMIT :limit
            """),
            {"job_id": job_id, "offset": offset, "limit": limit},
        )
        rows = result.fetchall()

        logs = [
            {
                "level": row._mapping["level"],
                "message": row._mapping["message"],
                "created_at": row._mapping["created_at"].isoformat() if row._mapping["created_at"] else None,
            }
            for row in rows
        ]

        return {
            "logs": logs,
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    def add_log(self, job_id: int, level: str, message: str):
        """写入任务日志"""
        self.db.execute(
            text("""
                INSERT INTO etl_job_run_log (job_id, level, message, created_at)
                VALUES (:job_id, :level, :message, NOW())
            """),
            {"job_id": job_id, "level": level, "message": message},
        )
        self.db.commit()

    def run_job(self, job_name: str, biz_date: str | None, force: bool) -> dict:
        """
        触发 ETL 任务（降级：etl_backfill_task 表不存在，
        返回提示信息）。
        """
        return {
            "task_id": None,
            "job_name": job_name,
            "biz_date": biz_date,
            "message": "ETL 触发接口暂未对接，当前仅支持查询",
        }

    def init_job_run(self, job_name: str, biz_date: str | None = None) -> int:
        """创建 ETL 任务记录，返回 job_id"""
        result = self.db.execute(
            text("""
                INSERT INTO etl_job_run (job_name, biz_date, status, start_time, created_at)
                VALUES (:job_name, :biz_date, 'RUNNING', NOW(), NOW())
                RETURNING id
            """),
            {"job_name": job_name, "biz_date": biz_date}
        )
        self.db.commit()
        return result.fetchone()[0]

    def update_job_run(
        self,
        job_id: int,
        status: str,
        rows_raw: int | None = None,
        rows_written: int | None = None,
        error_message: str | None = None,
    ):
        """更新 ETL 任务状态"""
        updates = ["status = :status", "end_time = NOW()"]
        params = {"job_id": job_id, "status": status}
        if rows_raw is not None:
            updates.append("rows_raw = :rows_raw")
            params["rows_raw"] = rows_raw
        if rows_written is not None:
            updates.append("rows_written = :rows_written")
            params["rows_written"] = rows_written
        if error_message is not None:
            updates.append("error_message = :error_message")
            params["error_message"] = error_message

        self.db.execute(
            text(f"UPDATE etl_job_run SET {', '.join(updates)} WHERE id = :job_id"),
            params
        )
        self.db.commit()

    def cancel_job(self, job_id: int) -> bool:
        self.update_job_run(job_id, "CANCELLED")
        return True
