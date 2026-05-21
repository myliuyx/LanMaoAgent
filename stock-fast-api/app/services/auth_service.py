import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.repositories.auth_repository import AuthRepository
from app.core.config import settings

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AuthRepository(db)

    def login(self, username: str, password: str) -> dict | None:
        user = self.repo.get_user_by_username(username)
        if not user:
            return None
        if not self.repo.verify_password(password, user["password_hash"]):
            return None

        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
        payload = {"sub": str(user["id"]), "exp": expire}
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        return {
            "token": token,
            "expires_in": settings.JWT_EXPIRE_HOURS * 3600,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
            },
        }

    def verify(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = int(payload["sub"])
            user = self.repo.get_user_by_id(user_id)
            if user:
                return {
                    "valid": True,
                    "user": {
                        "id": user["id"],
                        "username": user["username"],
                        "role": user["role"],
                    },
                }
        except Exception:
            pass
        return {"valid": False, "user": None}
