# Routers 层 - 路由定义

> 尽量薄的接入层：接收参数 → 调用 Service → 返回统一响应。
> **禁止在这里写业务逻辑和 SQL**。

## 文件清单

| 文件 | 路径前缀 | 接口数 | 说明 |
|------|---------|--------|------|
| `auth.py` | `/api/v1/auth` | 2 | 认证 |
| `dashboard.py` | `/api/v1/dashboard` | 3 | 首页 |
| `selection.py` | `/api/v1/selection` | 4 | 选股 |
| `stocks.py` | `/api/v1/stocks` | 8 | 个股 |
| `jobs.py` | `/api/v1/jobs` | 5 | 任务 |
| `boards.py` | `/api/v1/boards` | 3 | 板块 |
| `coverage.py` | `/api/v1/coverage` | 3 | 覆盖 |
| `backfill.py` | `/api/v1/backfill` | 2 | 补历史 |
| `system.py` | `/api/v1/system` | 1 | 系统 |

## 完整接口清单

```
Auth
  POST   /api/v1/auth/login                                  login
  GET    /api/v1/auth/verify                                 verify

Dashboard
  GET    /api/v1/dashboard/summary                           get_dashboard_summary
  GET    /api/v1/dashboard/jobs                              get_recent_jobs
  GET    /api/v1/dashboard/coverage                          get_dashboard_coverage

Selection
  GET    /api/v1/selection/dates                             get_selection_dates
  GET    /api/v1/selection/industries                         get_selection_industries
  POST   /api/v1/selection/query                              query_selection
  POST   /api/v1/selection/export                             export_selection

Stocks
  GET    /api/v1/stocks/search                                search_stocks
  GET    /api/v1/stocks/{symbol}/profile                      get_stock_profile
  GET    /api/v1/stocks/{symbol}/daily                        get_stock_daily
  GET    /api/v1/stocks/{symbol}/factors                      get_stock_factors
  GET    /api/v1/stocks/{symbol}/finance                     get_stock_finance
  GET    /api/v1/stocks/{symbol}/boards                       get_stock_boards
  GET    /api/v1/stocks/{symbol}/coverage                     get_stock_coverage
  GET    /api/v1/stocks/{symbol}/latest                      get_stock_latest

Jobs
  GET    /api/v1/jobs                                         list_jobs
  GET    /api/v1/jobs/{job_id}                               get_job_detail
  GET    /api/v1/jobs/{job_id}/logs                          get_job_logs
  POST   /api/v1/jobs/run                                     run_job
  POST   /api/v1/jobs/{job_id}/cancel                        cancel_job

Boards
  GET    /api/v1/boards                                       list_boards
  GET    /api/v1/boards/{board_code}                         get_board
  GET    /api/v1/boards/{board_code}/members                  get_board_members

Coverage
  GET    /api/v1/coverage                                     get_coverage_list
  GET    /api/v1/coverage/summary                            get_coverage_summary
  GET    /api/v1/coverage/{symbol}                           get_coverage_detail

Backfill
  POST   /api/v1/backfill/run                                 run_backfill
  GET    /api/v1/backfill/status/{task_id}                    get_backfill_status

System
  GET    /api/v1/system/meta                                  get_meta
```

## 路由写法规范

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.deps import get_db
from app.core.response import success_response
from app.services.stock_service import StockService

router = APIRouter(prefix="/stocks", tags=["Stocks"])

@router.get("/{symbol}/profile", summary="获取股票基础信息")
def get_stock_profile(symbol: str, db: Session = Depends(get_db)):
    service = StockService(db)
    data = service.get_profile(symbol)
    return success_response(data)
```

## Tag 分组（用于 Swagger 文档）

| Router | Tag |
|--------|-----|
| `auth.py` | Auth |
| `dashboard.py` | Dashboard |
| `selection.py` | Selection |
| `stocks.py` | Stocks |
| `jobs.py` | Jobs |
| `boards.py` | Boards |
| `coverage.py` | Coverage |
| `backfill.py` | Backfill |
| `system.py` | System |

## 注册位置

所有 Router 在 `app/main.py` 中注册：

```python
from app.routers import auth, dashboard, selection, stocks, jobs, coverage, boards, backfill, system

app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_PREFIX)
# ... 其余 7 个
```

## 统一返回

每个路由最后统一返回 `success_response(data)` 或 `error_response(code, message)`。
