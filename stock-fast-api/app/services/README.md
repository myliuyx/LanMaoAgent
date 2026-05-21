# Services 层 - 业务逻辑

> 业务大脑，负责数据聚合和流程控制。每个 Service 对应一个业务域。
> **不要在这里写 SQL**，那是 Repository 的职责。

## 文件清单

| 文件 | 类 | 方法 | 说明 |
|------|-----|------|------|
| `auth_service.py` | `AuthService` | `login()` / `verify()` | 认证逻辑 |
| `dashboard_service.py` | `DashboardService` | `get_summary()` / `get_recent_jobs()` / `get_coverage_summary()` | 首页数据聚合 |
| `selection_service.py` | `SelectionService` | `query()` / `get_dates()` / `get_industries()` | 选股查询 |
| `stock_service.py` | `StockService` | `get_profile()` / `get_latest()` / `search()` / `get_daily()` / `get_factors()` / `get_finance()` / `get_boards()` / `get_coverage()` | 个股详情聚合 |
| `job_service.py` | `JobService` | `list_jobs()` / `get_job()` / `get_logs()` / `run_job()` / `cancel_job()` | 任务管理 |
| `coverage_service.py` | `CoverageService` | `get_summary()` / `get_list()` / `get_detail()` | 覆盖范围 |
| `board_service.py` | `BoardService` | `list_boards()` / `get_board()` / `get_members()` | 板块查询 |
| `backfill_service.py` | `BackfillService` | `run_backfill()` / `get_status()` | 补历史任务 |

## 方法签名速查

### AuthService

```python
class AuthService:
    def login(self, username: str, password: str) -> dict | None  # 当前 Mock 返回 dict
    def verify(self, token: str) -> dict  # 当前 Mock 返回 dict
```

### DashboardService

```python
class DashboardService:
    def get_summary(self) -> dict  # 当前 Mock 返回 dict
    def get_recent_jobs(self, limit: int = 10) -> list
    def get_coverage_summary(self) -> dict  # {stocks_with_full_daily, ...}
```

### SelectionService

```python
class SelectionService:
    def query(self, req: SelectionQueryRequest) -> dict  # 当前 Mock 返回 dict
    def get_dates(self, start_date, end_date, limit) -> list
    def get_industries(self) -> list
```

### StockService

```python
class StockService:
    def get_profile(self, symbol: str) -> dict  # 当前 Mock 返回 dict
    def get_latest(self, symbol: str) -> dict
    def search(self, keyword: str, limit: int) -> list
    def get_daily(self, symbol, start_date, end_date, limit, adjust) -> list
    def get_factors(self, symbol, trade_date, limit) -> list
    def get_finance(self, symbol, limit) -> list
    def get_boards(self, symbol) -> list
    def get_coverage(self, symbol) -> list
```

### JobService

```python
class JobService:
    def list_jobs(self, page, page_size, job_name, status, biz_date) -> dict  # 当前 Mock 返回 dict
    def get_job(self, job_id: int) -> dict | None
    def get_logs(self, job_id, offset, limit) -> dict
    def run_job(self, job_name, biz_date, force) -> dict
    def cancel_job(self, job_id: int) -> bool
```

### CoverageService

```python
class CoverageService:
    def get_summary(self) -> dict
    def get_list(self, symbol, data_type, is_full_history, page, page_size) -> dict  # 当前 Mock 返回 dict
    def get_detail(self, symbol) -> dict  # {symbol, name, coverages: [...]}
```

### BoardService

```python
class BoardService:
    def list_boards(self, board_type, keyword, page, page_size) -> dict  # 当前 Mock 返回 dict
    def get_board(self, board_code) -> dict | None
    def get_members(self, board_code, trade_date, page, page_size, sort_by, sort_order) -> dict
```

### BackfillService

```python
class BackfillService:
    def run_backfill(self, symbol, data_type, start_date, end_date, force) -> dict
    def get_status(self, task_id) -> dict
```

## Repository 调用约定

```python
from app.repositories import StockRepository, JobRepository

class StockService:
    def __init__(self, db: Session):
        self.repo = StockRepository(db)
    
    def get_profile(self, symbol: str) -> StockProfileData:
        raw = self.repo.get_profile(symbol)  # dict from DB
        return StockProfileData(**raw)        # convert to Schema
```

## 当前状态

- ✅ 所有 Service 方法已定义（Mock 实现，返回 dict）
- 🔄 Repository 层为 Mock 数据
- 🎯 真实实现：Repository 切换真实 SQL → Service 层做 Schema 序列化

## 类型注解说明

当前返回类型标注为 `dict` 是因为 Repository 层是 Mock 数据，直接透传。
真实实现时，Repository 返回 dict，Service 层再转为 Schema 对象返回。
如 `get_summary()` 的目标是 `DashboardSummaryData`，`get_profile()` 的目标是 `StockProfileData`。
