from sqlalchemy.orm import Session
from app.repositories.coverage_repository import CoverageRepository


class CoverageService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CoverageRepository(db)

    def get_summary(self) -> dict:
        return self.repo.get_summary()

    def get_list(self, symbol: str | None, data_type: str | None, is_full_history: bool | None, page: int, page_size: int) -> dict:
        return self.repo.get_list(symbol, data_type, is_full_history, page, page_size)

    def get_detail(self, symbol: str) -> dict:
        return self.repo.get_detail(symbol)
