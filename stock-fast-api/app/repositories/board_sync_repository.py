"""Board sync repository - 板块数据同步写入（无 trade_date 维度）"""
from datetime import date
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import text


class BoardSyncRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_board_master(
        self,
        board_code: str,
        board_name: str,
        board_type: str | None = None,
        source: str = "efinance",
    ) -> None:
        """
        写入或更新 dwd_board_master。
        board_code 唯一键，冲突则更新 board_name / board_type / source。
        """
        self.db.execute(
            text("""
                INSERT INTO dwd_board_master (board_code, board_name, board_type, source, updated_at)
                VALUES (:board_code, :board_name, :board_type, :source, NOW())
                ON CONFLICT (board_code) DO UPDATE SET
                    board_name = EXCLUDED.board_name,
                    board_type = COALESCE(EXCLUDED.board_type, dwd_board_master.board_type),
                    source = EXCLUDED.source,
                    updated_at = NOW()
            """),
            {
                "board_code": board_code,
                "board_name": board_name,
                "board_type": board_type,
                "source": source,
            },
        )

    def upsert_board_relation(
        self,
        symbol: str,
        board_code: str,
        board_type: str | None = None,
        relation_source: str = "efinance",
    ) -> None:
        """
        写入或更新 dwd_board_relation（无 trade_date 维度）。
        使用 ON CONFLICT DO UPDATE 实现 upsert。
        """
        self.db.execute(
            text("""
                INSERT INTO dwd_board_relation (symbol, board_code, board_type, relation_source, updated_at)
                VALUES (:symbol, :board_code, :board_type, :relation_source, NOW())
                ON CONFLICT (symbol, board_code) DO UPDATE SET
                    board_type = EXCLUDED.board_type,
                    relation_source = EXCLUDED.relation_source,
                    updated_at = NOW()
            """),
            {
                "symbol": symbol,
                "board_code": board_code,
                "board_type": board_type,
                "relation_source": relation_source,
            },
        )

    def clear_relations_by_symbol(self, symbol: str) -> int:
        """
        清除某只股票的所有板块关系（用于全量替换）。
        返回删除数量。
        """
        result = self.db.execute(
            text("DELETE FROM dwd_board_relation WHERE symbol = :symbol"),
            {"symbol": symbol},
        )
        return result.rowcount

    def batch_upsert_relations(
        self,
        symbol: str,
        boards: list[dict[str, Any]],
    ) -> None:
        """
        批量 upsert 某只股票的板块关系（全量替换）。
        先删后插，boards: [{"board_code": ..., "board_type": ...}, ...]
        """
        self.clear_relations_by_symbol(symbol)
        for b in boards:
            self.db.execute(
                text("""
                    INSERT INTO dwd_board_relation (symbol, board_code, board_type, relation_source, updated_at)
                    VALUES (:symbol, :board_code, :board_type, 'efinance', NOW())
                """),
                {
                    "symbol": symbol,
                    "board_code": b["board_code"],
                    "board_type": b.get("board_type"),
                },
            )
