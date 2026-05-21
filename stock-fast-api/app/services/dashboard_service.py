from sqlalchemy.orm import Session
from app.repositories.dashboard_repository import DashboardRepository


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DashboardRepository(db)

    def get_summary(self) -> dict:
        return self.repo.get_summary()

    def get_recent_jobs(self, limit: int) -> list:
        return self.repo.get_recent_jobs(limit=limit)

    def get_coverage_summary(self) -> dict:
        return self.repo.get_coverage_summary()

    def watchlist_analysis(self, symbols: list[str]) -> dict:
        return self.repo.watchlist_analysis(symbols)
