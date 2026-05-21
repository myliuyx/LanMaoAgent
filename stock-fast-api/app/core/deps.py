from collections.abc import Generator
from typing import Optional

from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.config import settings


def get_db() -> Generator[Session, None, None]:
    """数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    authorization: Optional[str] = Header(None, description="Bearer Token"),
    db: Session = Depends(get_db),
) -> dict:
    """
    JWT 认证依赖。

    用法：
        @router.get("/protected")
        def protected_route(user: dict = Depends(get_current_user)):
            ...

    从 Authorization: Bearer <token> 头提取并验证 token。
    验证失败返回 401，前端据此跳转登录页。
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="令牌格式无效，请使用 Bearer Token")

    token = authorization[7:]
    try:
        import jwt

        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = int(payload["sub"])

    except (jwt.ExpiredSignatureError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="令牌无效或已过期")

    # 延迟导入避免循环
    from app.repositories.auth_repository import AuthRepository

    repo = AuthRepository(db)
    user = repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    return user
