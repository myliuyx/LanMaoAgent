from sqlalchemy.orm import Session
from app.repositories.board_repository import BoardRepository


class BoardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BoardRepository(db)

    def list_boards(self, board_type: str | None, keyword: str | None, page: int, page_size: int) -> dict:
        return self.repo.list_boards(board_type, keyword, page, page_size)

    def get_board(self, board_code: str) -> dict | None:
        return self.repo.get_board(board_code)

    def get_members(self, board_code: str, trade_date: str | None, page: int, page_size: int, sort_by: str, sort_order: str) -> dict:
        return self.repo.get_members(board_code, trade_date, page, page_size, sort_by, sort_order)
