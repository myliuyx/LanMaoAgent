# -*- coding: utf-8 -*-
"""全量同步脚本：读取 dwd_security_master 所有股票，同步板块数据"""
import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.db import SessionLocal
from app.services.board_sync_service import BoardSyncService


BATCH_SIZE = 20
DELAY_BETWEEN_BATCHES = 1.0
LOG_FILE = "/tmp/board_sync_progress.json"


def get_all_symbols(session) -> list[str]:
    result = session.execute(
        text("SELECT symbol FROM dwd_security_master WHERE status = 'LISTED' ORDER BY symbol")
    )
    return [row[0] for row in result.fetchall()]


def log_progress(data):
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False)


def main():
    session = SessionLocal()
    try:
        symbols = get_all_symbols(session)
        print(f"Total: {len(symbols)} stocks")
    finally:
        session.close()

    total = len(symbols)
    success = 0
    fail = 0
    total_boards = 0
    errors = []

    for i in range(0, total, BATCH_SIZE):
        batch = symbols[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"\n[Batch {batch_num}] Processing {len(batch)} stocks...")

        for symbol in batch:
            # Create fresh service+session per stock
            db_session = SessionLocal()
            try:
                service = BoardSyncService(db_session)
                result = service.sync_stock(symbol)
                if result["success"]:
                    success += 1
                    total_boards += result.get("boards_synced", 0)
                else:
                    fail += 1
                    errors.append({"symbol": symbol, "error": result.get("error", "unknown")})
                    print(f"  FAIL {symbol}: {result.get('error', 'unknown')}")
            except Exception as e:
                fail += 1
                print(f"  EXC {symbol}: {e}")
            finally:
                db_session.close()

            time.sleep(0.3)

        log_progress({
            "total": total,
            "processed": min(i + BATCH_SIZE, total),
            "success": success,
            "fail": fail,
            "total_boards": total_boards,
        })
        print(f"  Done: {min(i + BATCH_SIZE, total)}/{total}")
        time.sleep(DELAY_BETWEEN_BATCHES)

    log_progress({
        "total": total,
        "processed": total,
        "success": success,
        "fail": fail,
        "total_boards": total_boards,
        "done": True,
        "errors": errors[:50],
    })

    print(f"\n{'=' * 50}")
    print(f"Sync done: {success} ok, {fail} failed, {total_boards} total boards")
    if success > 0:
        print(f"Avg boards/stock: {total_boards / success:.1f}")
    if errors:
        print(f"First few errors:")
        for e in errors[:5]:
            print(f"  {e['symbol']}: {e['error']}")


if __name__ == "__main__":
    main()
