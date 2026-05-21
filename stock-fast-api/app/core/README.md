# Core 层 - 核心公共模块

> 配置、数据库、异常、响应、日志。不包含业务逻辑。

## 文件清单

| 文件 | 类/函数 | 说明 |
|------|---------|------|
| `config.py` | `settings`（单例） | 环境变量配置：DB / APP_NAME / API_PREFIX |
| `db.py` | `engine`, `SessionLocal`, `get_db()` | SQLAlchemy 数据库连接 |
| `deps.py` | `get_db()` | FastAPI 依赖注入（yield db） |
| `exceptions.py` | `BizException`, `NotFoundException` | 自定义业务异常 |
| `response.py` | `success_response()`, `error_response()` | 统一响应封装 |
| `logger.py` | `logger` | 全局日志对象 |
| `__init__.py` | - | 统一导出 |

## 配置 (config.py)

```python
from app.core.config import settings

settings.APP_NAME       # = "A股股票数据API"
settings.APP_VERSION    # = "0.1.0"
settings.API_PREFIX     # = "/api/v1"
settings.DB_HOST        # = "192.168.3.16"
settings.DB_PORT        # = 5432
settings.DB_NAME        # = "stock_cache_system"
settings.DB_USER        # = "postgres"
settings.DB_PASSWORD    # = "H7k9P2mX5wR1"
settings.database_url   # 计算属性
```

## 数据库 (db.py)

```python
from app.core.db import get_db, engine, SessionLocal

# 依赖注入用法
@router.get("/")
def handler(db: Session = Depends(get_db)):
    ...

# 直接使用
db = SessionLocal()
try:
    ...
finally:
    db.close()
```

## 响应封装 (response.py)

```python
from app.core.response import success_response, error_response

# 成功响应
return success_response(data)          # → {code: 0, message: "success", data: ...}
return success_response(None)         # → {code: 0, message: "success", data: null}

# 失败响应
return error_response(code=4041, message="stock not found")
# → {code: 4041, message: "stock not found", data: null}
```

## 异常 (exceptions.py)

```python
from app.core.exceptions import BizException, NotFoundException

# 抛出业务异常（被 main.py 的全局异常处理器捕获）
raise BizException(code=4041, message="stock not found")
raise NotFoundException(code=4042, message="board not found")

# HTTPException（非业务异常，由 FastAPI 自行处理）
from fastapi import HTTPException
raise HTTPException(status_code=401, detail="invalid token")
```

## 日志 (logger.py)

```python
from app.core.logger import logger

logger.info("任务启动: %s", job_name)
logger.warning("数据库连接超时")
logger.error("写入失败: %s", error)
```

## 全局异常处理 (main.py)

```python
from fastapi import FastAPI, Request, JSONResponse
from app.core.exceptions import BizException

@app.exception_handler(BizException)
async def biz_exception_handler(request: Request, exc: BizException):
    return JSONResponse(
        status_code=200,  # 业务异常不走 4xx，走 200 + code 字段
        content={"code": exc.code, "message": exc.message, "data": None},
    )
```
