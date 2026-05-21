from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.response import success_response
from app.core.exceptions import BizException
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", summary="用户登录")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    result = service.login(req.username, req.password)
    if result is None:
        raise BizException(code=1002, message="用户名或密码错误")
    return success_response(result)


def verify_token(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="invalid token format")
    return authorization[7:]


@router.get("/verify", summary="验证Token")
def verify(db: Session = Depends(get_db), token: str = Depends(verify_token)):
    service = AuthService(db)
    result = service.verify(token)
    return success_response(result)
