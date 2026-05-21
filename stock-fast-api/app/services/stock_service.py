from sqlalchemy.orm import Session
from app.repositories.stock_repository import StockRepository


class StockService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StockRepository(db)

    def get_profile(self, symbol: str) -> dict:
        return self.repo.get_profile(symbol)

    def get_latest(self, symbol: str) -> dict:
        return self.repo.get_latest(symbol)

    def search(self, keyword: str, limit: int) -> list:
        return self.repo.search_stocks(keyword, limit)

    def get_daily(self, symbol: str, start_date: str | None, end_date: str | None,
                  limit: int, adjust: str) -> list:
        return self.repo.get_daily(symbol, start_date, end_date, limit, adjust)

    def get_factors(self, symbol: str, trade_date: str | None, limit: int) -> list:
        return self.repo.get_factors(symbol, trade_date, limit)

    def get_finance(self, symbol: str, limit: int) -> list:
        return self.repo.get_finance(symbol, limit)

    def get_boards(self, symbol: str) -> list:
        return self.repo.get_boards(symbol)

    def get_adjust_factors(self, symbol: str, start_date: str | None, end_date: str | None, limit: int) -> list:
        return self.repo.get_adjust_factors(symbol, start_date, end_date, limit)
