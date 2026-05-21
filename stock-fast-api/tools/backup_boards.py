# -*- coding: utf-8 -*-
"""一次性脚本：备份板块数据到 JSON 文件"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.db import SessionLocal


def backup_table(session, table: str, output_path: str) -> int:
    """导出表全部数据到 JSON 文件"""
    result = session.execute(text(f"SELECT * FROM {table}"))
    rows = result.fetchall()
    items = [dict(r._mapping) for r in rows]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2, default=str)
    return len(items)


def main():
    out_dir = "/tmp"
    master_path = os.path.join(out_dir, "board_master_backup.json")
    relation_path = os.path.join(out_dir, "board_relation_backup.json")

    session = SessionLocal()
    try:
        n = backup_table(session, "dwd_board_master", master_path)
        print(f"✅ dwd_board_master: {n} 条 → {master_path}")
        n = backup_table(session, "dwd_board_relation", relation_path)
        print(f"✅ dwd_board_relation: {n} 条 → {relation_path}")
    finally:
        session.close()

    print("Done.")


if __name__ == "__main__":
    main()
