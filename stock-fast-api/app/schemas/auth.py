from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_in: int
    user: "UserInfo"


class UserInfo(BaseModel):
    id: int
    username: str
    role: str


class VerifyResponse(BaseModel):
    valid: bool
    user: UserInfo | None
