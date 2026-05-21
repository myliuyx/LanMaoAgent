"""
API 限流中间件

基于滑动窗口算法的内存限流实现。
支持：
- 按 IP 限流（未认证请求）
- 按用户 ID 限流（认证请求）
- 差异化限流（login 接口更严格）
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class RateLimitBucket:
    """限流桶"""
    count: int = 0
    window_start: float = field(default_factory=time.time)

    def is_expired(self, window_seconds: int) -> bool:
        return time.time() - self.window_start > window_seconds

    def reset(self):
        self.count = 0
        self.window_start = time.time()


class RateLimiter:
    """
    滑动窗口限流器

    - login_limit: login 接口 5次/分钟/IP
    - api_limit: 其他 API 100次/分钟/用户 或 IP
    """

    def __init__(self):
        self._lock = Lock()
        # login 限流：key = client_ip
        self._login_buckets: dict[str, RateLimitBucket] = defaultdict(RateLimitBucket)
        # API 限流：key = user_id 或 client_ip
        self._api_buckets: dict[str, RateLimitBucket] = defaultdict(RateLimitBucket)

        # 限流配置（秒）
        self._login_window = 60        # 1分钟窗口
        self._login_max = 5            # 5次/分钟
        self._api_window = 60          # 1分钟窗口
        self._api_max = 100            # 100次/分钟

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP，优先从 X-Forwarded-For 获取"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_key(self, request: Request, user_id: Optional[str] = None) -> str:
        """生成限流 key"""
        if user_id:
            return f"user:{user_id}"
        return f"ip:{self._get_client_ip(request)}"

    def check_login(self, request: Request) -> bool:
        """检查 login 请求是否超过限流"""
        key = self._get_client_ip(request)
        with self._lock:
            bucket = self._login_buckets[key]
            if bucket.is_expired(self._login_window):
                bucket.reset()
            bucket.count += 1
            return bucket.count <= self._login_max

    def check_api(self, request: Request, user_id: Optional[str] = None) -> bool:
        """检查 API 请求是否超过限流"""
        key = self._get_key(request, user_id)
        with self._lock:
            bucket = self._api_buckets[key]
            if bucket.is_expired(self._api_window):
                bucket.reset()
            bucket.count += 1
            return bucket.count <= self._api_max

    def get_remaining_login(self, request: Request) -> int:
        """获取 login 剩余请求次数"""
        key = self._get_client_ip(request)
        with self._lock:
            bucket = self._login_buckets.get(key)
            if not bucket or bucket.is_expired(self._login_window):
                return self._login_max
            return max(0, self._login_max - bucket.count)

    def get_remaining_api(self, request: Request, user_id: Optional[str] = None) -> int:
        """获取 API 剩余请求次数"""
        key = self._get_key(request, user_id)
        with self._lock:
            bucket = self._api_buckets.get(key)
            if not bucket or bucket.is_expired(self._api_window):
                return self._api_max
            return max(0, self._api_max - bucket.count)


# 全局限流器实例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    限流中间件

    对 /api/v1/auth/login 进行严格限流（5次/分钟/IP）
    对其他 /api/v1/* 进行通用限流（100次/分钟/用户 或 IP）
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 仅对 /api/v1/* 进行限流
        if not path.startswith("/api/v1"):
            return await call_next(request)

        limiter = get_rate_limiter()
        client_ip = limiter._get_client_ip(request)

        # 提取 Authorization header 获取 user_id（不验证 token，仅用于限流 key）
        user_id: Optional[str] = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                import jwt
                from app.core.config import settings
                token = auth_header[7:]
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM],
                    options={"verify_exp": False},
                )
                user_id = str(payload.get("sub", ""))
            except Exception:
                pass

        # login 接口严格限流
        if path == "/api/v1/auth/login":
            if not limiter.check_login(request):
                raise HTTPException(
                    status_code=429,
                    detail=f"请求过于频繁，请 {60} 秒后重试。剩余尝试次数: 0",
                )
            remaining = limiter.get_remaining_login(request)
        else:
            if not limiter.check_api(request, user_id):
                raise HTTPException(
                    status_code=429,
                    detail=f"请求过于频繁，请稍后重试。",
                )
            remaining = limiter.get_remaining_api(request, user_id)

        response = await call_next(request)

        # 在响应头添加限流信息
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
