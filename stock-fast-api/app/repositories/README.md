# Repositories 层 - 数据访问

> 直接和数据库交互，编写 SQL，返回原始查询结果。
> **隔离数据库实现细节**，上层 Service 不知道 SQL 长什么样。

## 文件清单

| 文件 | 类 | 方法 | 说明 |
|------|-----|------|------|
| `dashboard_repository.py` | `DashboardRepository` | `get_summary()` / `get_recent_jobs()` / `get_coverage_summary()` | 首页数据 |
| `selection_repository.py` | `SelectionRepository` | `query_selection()` / `get_dates()` / `get_industries()` | 选股数据 |
| `stock_repository.py` | `StockRepository` | `get_profile()` / `get_latest()` / `search_stocks()` / `get_daily()` / `get_factors()` / `get_finance()` / `get_boards()` / `get_coverage()` | 个股数据 |
| `job_repository.py` | `JobRepository` | `list_jobs()` / `get_job()` / `get_logs()` / `run_job()` / `cancel_job()` | ETL 任务 |
| `coverage_repository.py` | `CoverageRepository` | `get_summary()` / `get_list()` / `get_detail()` | 覆盖范围 |
| `board_repository.py` | `BoardRepository` | `list_boards()` / `get_board()` / `get_members()` | 板块数据 |
| `backfill_repository.py` | `BackfillRepository` | `run_backfill()` / `get_status()` | 补历史任务 |

## 方法签名速查

### DashboardRepository

```python
class DashboardRepository:
    def get_summary(self) -> dict
    def get_recent_jobs(self, limit: int) -> List[dict]
    def get_coverage_summary(self) -> dict
```

### SelectionRepository

```python
class SelectionRepository:
    def query_selection(self, trade_date, filters, sort_by, sort_order,
                        page, page_size) -> dict  # {list, page, page_size, total}
    def get_dates(self, start_date, end_date, limit) -> List[str]
    def get_industries(self) -> List[str]
```

### StockRepository

```python
class StockRepository:
    def get_profile(self, symbol: str) -> dict
    def get_latest(self, symbol: str) -> dict
    def search_stocks(self, keyword: str, limit: int) -> List[dict]
    def get_daily(self, symbol, start_date, end_date, limit, adjust) -> List[dict]
    def get_factors(self, symbol, trade_date, limit) -> List[dict]
    def get_finance(self, symbol, limit) -> List[dict]
    def get_boards(self, symbol) -> List[dict]
    def get_coverage(self, symbol) -> List[dict]
```

### JobRepository

```python
class JobRepository:
    def list_jobs(self, page, page_size, job_name, status, biz_date) -> dict
    def get_job(self, job_id: int) -> dict | None
    def get_logs(self, job_id, offset, limit) -> dict
    def run_job(self, job_name, biz_date, force) -> dict
    def cancel_job(self, job_id: int) -> bool
```

### CoverageRepository

```python
class CoverageRepository:
    def get_summary(self) -> dict
    def get_list(self, symbol, data_type, is_full_history, page, page_size) -> dict
    def get_detail(self, symbol) -> dict
```

### BoardRepository

```python
class BoardRepository:
    def list_boards(self, board_type, keyword, page, page_size) -> dict
    def get_board(self, board_code) -> dict | None
    def get_members(self, board_code, trade_date, page, page_size,
                    sort_by, sort_order) -> dict
```

### BackfillRepository

```python
class BackfillRepository:
    def run_backfill(self, symbol, data_type, start_date, end_date, force) -> dict
    def get_status(self, task_id) -> dict
```

## Repository 基类约定

```python
class BaseRepository:
    def __init__(self, db: Session):
        self.db = db
```

## 当前状态

- ✅ 所有 Repository 已定义
- 🔄 当前为 **Mock 数据** 实现
- 🎯 真实实现：替换 Mock → SQLAlchemy ORM 或原生 SQL

## 落地优先级

| 优先级 | Repository | 原因 |
|--------|-----------|------|
| P0 | StockRepository | 个股是核心数据 |
| P0 | JobRepository | 任务管理是核心功能 |
| P1 | SelectionRepository | 选股查询使用频繁 |
| P1 | DashboardRepository | 首页每次打开都调 |
| P2 | CoverageRepository | 使用频率相对低 |
| P2 | BoardRepository | 板块数据量适中 |
| P3 | BackfillRepository | 手工操作，频率最低 |
