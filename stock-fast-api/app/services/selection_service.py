from sqlalchemy.orm import Session
from app.repositories.selection_repository import SelectionRepository
from app.schemas.selection import SelectionQueryRequest


class SelectionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SelectionRepository(db)

    def query(self, req: SelectionQueryRequest) -> dict:
        return self.repo.query_selection(req)

    def get_dates(self, start_date: str | None, end_date: str | None, limit: int) -> list:
        return self.repo.get_dates(start_date, end_date, limit)

    def get_industries(self) -> list:
        return self.repo.get_industries()

    def get_selection_top(self, days: int, limit: int) -> list[dict]:
        return self.repo.get_selection_top(days, limit)
