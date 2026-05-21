import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

logger = logging.getLogger("stock_api")


class AuthRepository:
    """认证仓储层，直接操作 app_user 表"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str) -> Optional[dict]:
        """根据用户名查询用户，返回 dict 或 None"""
        result = self.db.execute(
            text("""
                SELECT id, username, password_hash, role, is_active, created_at
                FROM app_user
                WHERE username = :username AND is_active = true
            """),
            {"username": username},
        )
        row = result.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "username": row[1],
            "password_hash": row[2],
            "role": row[3],
            "is_active": row[4],
            "created_at": row[5],
        }

    def verify_password(self, plain_password: str, stored_hash: str) -> bool:
        """验证密码（仅支持 bcrypt hash）"""
        if not stored_hash:
            return False

        if not stored_hash.startswith(("$2b$", "$2y$", "$2a$")):
            logger.error("Invalid password hash format - expected bcrypt hash")
            return False

        if not HAS_BCRYPT:
            logger.error("bcrypt library not installed, cannot verify password")
            return False

        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            stored_hash.encode("utf-8"),
        )

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """根据 ID 查询用户（用于 token 验证后获取用户信息）"""
        result = self.db.execute(
            text("""
                SELECT id, username, role, is_active
                FROM app_user
                WHERE id = :user_id AND is_active = true
            """),
            {"user_id": user_id},
        )
        row = result.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "username": row[1],
            "role": row[2],
            "is_active": row[3],
        }
