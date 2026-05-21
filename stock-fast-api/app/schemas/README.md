# Schemas 层 - DTO 模型定义

> 定义所有请求/响应数据结构，每个 Schema 对应一个业务域。

## 文件清单

| 文件 | 用途 |
|------|------|
| `common.py` | 通用结构：`ApiResponse[T]`、`PageData[T]` |
| `auth.py` | 登录请求/响应、用户信息、Token 验证响应 |
| `dashboard.py` | 首页摘要数据 |
| `selection.py` | 选股过滤器、查询请求、选股项、分页数据 |
| `stock.py` | 股票 profile、latest 行情 |
| `job.py` | 任务项、任务列表分页、触发请求 |
| `coverage.py` | 覆盖摘要数据 |
| `board.py` | 板块列表请求、板块项、板块详情、成分股项 |
| `backfill.py` | 补历史触发请求、状态响应 |
| `system.py` | 系统配置摘要 |

## 通用结构

```python
from app.schemas import ApiResponse, PageData

# 统一响应
ApiResponse[T] = { code: int, message: str, data: T | None }

# 统一分页（注意是 list 不是 items）
PageData[T] = { list: List[T], page: int, page_size: int, total: int }
```

## 各 Schema 字段速查

### auth.py
```
LoginRequest         → username, password
LoginResponse        → token, expires_in, user: UserInfo
UserInfo             → id, username, role
VerifyResponse       → valid: bool, user: UserInfo | None
```

### dashboard.py
```
DashboardSummaryData → latest_trade_date, is_trade_day, stock_count,
                        daily_record_count, finance_record_count,
                        factor_record_count, today_job_success_count,
                        today_job_failed_count, selection_count
```

### selection.py
```
SelectionFilters     → keyword, exchange, is_st, industry_l1,
                        market_value_min/max, turnover_rate_min/max,
                        roe_min, revenue_yoy_min, net_profit_yoy_min,
                        is_new_high_60d, is_break_ma20, trend_score_min
SelectionQueryRequest → trade_date, filters, sort_by, sort_order, page, page_size
SelectionItem        → symbol, name, exchange, industry_l1, close,
                        change_pct, turnover_rate, market_value, ma20, ma60,
                        is_new_high_60d, trend_score, is_st, roe,
                        revenue_yoy, net_profit_yoy
```

### stock.py
```
StockProfileData     → symbol, ticker, exchange, name, full_name,
                        security_type, list_board, list_date, delist_date,
                        status, is_st, industry_l1, industry_l2, area
StockLatestData      → symbol, name, latest_trade_date, close, change_pct,
                        turnover_rate, market_value, pe_ttm, pb, ma20, ma60,
                        rsi_14, trend_score, roe, revenue_yoy, net_profit_yoy
```

### job.py
```
JobItem              → id, job_name, biz_date, status, start_time, end_time,
                        duration_ms, rows_raw, rows_written, error_message
RunJobRequest        → job_name, biz_date | None, force: bool
```

### coverage.py
```
CoverageSummaryData  → total_symbols, daily_fully_covered_symbols,
                        financial_fully_covered_symbols,
                        adjust_factor_fully_covered_symbols,
                        latest_daily_trade_date | None,
                        latest_financial_report_period | None
```

### board.py
```
BoardListRequest     → board_type | None, keyword | None, page, page_size
BoardItem            → board_code, board_name, board_type,
                        member_count | None, is_active
BoardDetailResponse  → board_code, board_name, board_type,
                        parent_board_code | None, is_active
BoardMemberItem      → symbol, name, exchange, close, change_pct,
                        turnover_rate, market_value, trend_score, industry_l1
```

### backfill.py
```
BackfillRunRequest   → symbol, data_type, start_date | None,
                        end_date | None, force: bool
BackfillStatusResponse → task_id, job_name, status,
                          progress | None, message | None
```

### system.py
```
SystemMetaResponse   → env, version, db_status,
                        latest_trade_date, scheduler_status
```

## 导入方式

```python
# 推荐：从 schemas 总出口取
from app.schemas import LoginRequest, JobItem, PageData, ApiResponse

# 也可以直接从具体文件取
from app.schemas.job import RunJobRequest
```
