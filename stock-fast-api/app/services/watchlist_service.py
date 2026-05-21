from sqlalchemy.orm import Session
from app.repositories.watchlist_repository import WatchlistRepository
from app.core.exceptions import NotFoundException, BizException


class WatchlistService:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.repo = WatchlistRepository(db)

    def get_watchlist(self, page: int, page_size: int) -> dict:
        """获取自选股列表（分页）。"""
        return self.repo.list_watchlist(self.user_id, page, page_size)

    def add_stock(self, symbol: str) -> dict:
        """
        添加股票到自选。
        - 校验股票是否存在且状态为 LISTED
        - 校验是否已在自选列表中
        """
        if not self.repo.is_stock_exists(symbol):
            raise NotFoundException(code=4041, message="股票不存在")

        if self.repo.check_watchlist(self.user_id, symbol):
            raise BizException(code=409, message="该股票已在自选列表中")

        return self.repo.add_watchlist(self.user_id, symbol)

    def remove_stock(self, symbol: str) -> bool:
        """从自选股删除。"""
        if not self.repo.check_watchlist(self.user_id, symbol):
            raise NotFoundException(code=4043, message="该股票不在自选列表中")

        return self.repo.delete_watchlist(self.user_id, symbol)

    def check_stock(self, symbol: str) -> dict:
        """检查股票是否在自选列表中。"""
        in_watchlist = self.repo.check_watchlist(self.user_id, symbol)
        return {
            "symbol": symbol,
            "in_watchlist": in_watchlist,
        }
