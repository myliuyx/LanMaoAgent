from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings, Settings
from app.core.exceptions import BizException
from app.core.response import error_response

logger = logging.getLogger("stock_api")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A股股票信息缓存系统 FastAPI 后端",
)

# CORS 中间件（仅在配置了 CORS_ORIGINS 时启用）
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
elif settings.CORS_ORIGINS == "*":
    # 明确允许全通配符（仅用于开发环境）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 注册限流中间件
from app.middleware.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# 注册路由
from app.routers import auth, dashboard, selection, stocks, jobs, coverage, boards, backfill, system, watchlist, strategy

# 注册定时任务
from app.scheduler import create_scheduler


# ─── 全局异常处理器 ────────────────────────────────────────────
@app.exception_handler(BizException)
async def biz_exception_handler(request: Request, exc: BizException):
    """
    业务异常全局处理器。
    根据错误码映射到对应 HTTP 状态码：
    - 认证/授权类（1001-1999）→ 401
    - 参数校验类（4001-4999）→ 400
    - 资源不存在类（4041-4049）→ 404
    - 服务端错误类（5001-5999）→ 500
    - 其他业务异常 → 200（保持向后兼容）
    """
    code = exc.code
    if 1001 <= code <= 1999:
        status_code = 401
    elif 4001 <= code <= 4999:
        status_code = 400
    elif 4041 <= code <= 4049:
        status_code = 404
    elif 5001 <= code <= 5999:
        status_code = 500
    else:
        status_code = 200  # 通用业务异常（如未知的 9999）

    return JSONResponse(
        status_code=status_code,
        content=error_response(code=exc.code, message=exc.message, data=None),
    )


# ─── 注册路由 ──────────────────────────────────────────────────
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_PREFIX)
app.include_router(selection.router, prefix=settings.API_PREFIX)
app.include_router(stocks.router, prefix=settings.API_PREFIX)
app.include_router(jobs.router, prefix=settings.API_PREFIX)
app.include_router(coverage.router, prefix=settings.API_PREFIX)
app.include_router(boards.router, prefix=settings.API_PREFIX)
app.include_router(backfill.router, prefix=settings.API_PREFIX)
app.include_router(system.router, prefix=settings.API_PREFIX)
app.include_router(watchlist.router, prefix=settings.API_PREFIX)
app.include_router(strategy.router, prefix=settings.API_PREFIX)


# ─── 启动/关闭事件 ────────────────────────────────────────────
scheduler = None


@app.on_event("startup")
async def startup_event():
    global scheduler
    # 校验关键配置
    settings.validate()
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("🚀 应用已启动，定时任务调度器运行中")


@app.on_event("shutdown")
async def shutdown_event():
    if scheduler:
        scheduler.shutdown()
        logger.info("🛑 应用已关闭，定时任务调度器已停止")


# ─── 健康检查 ──────────────────────────────────────────────────
@app.get("/", summary="健康检查")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
