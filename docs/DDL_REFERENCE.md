# DDL 脚本参考 / DDL Script Reference

本文档说明 `09_postgresql_ddl.sql` 的作用、表创建顺序及初始化检查方法。

---

## 1. 文件位置

```
stock-fast-api/docs/09_postgresql_ddl.sql
```

---

## 2. 脚本内容概述

该脚本一次性创建 16 张表，包含：

| 序号 | 表名 | 类型 | 说明 |
|------|------|------|------|
| 1 | `app_user` | 认证 | 用户认证表 |
| 2 | `dwd_security_master` | 维度表 | 股票主数据 |
| 3 | `dwd_trade_calendar` | 维度表 | 交易日历 |
| 4 | `dwd_stock_daily` | 事实表 | 股票日线行情 |
| 5 | `dwd_stock_adjust_factor` | 事实表 | 复权因子 |
| 6 | `dwd_stock_financial_indicator` | 事实表 | 财务指标 |
| 7 | `dwd_stock_factor_daily` | 事实表 | 日度技术因子 |
| 8 | `dwd_board_master` | 维度表 | 板块主表 |
| 9 | `dwd_board_relation` | 事实表 | 股票板块关系 |
| 10 | `mart_stock_selection_daily` | 派生表 | 选股宽表 |
| 11 | `mart_user_watchlist` | 派生表 | 用户自选股 |
| 12 | `etl_job_run` | ETL表 | 任务运行记录 |
| 13 | `etl_checkpoint` | ETL表 | 断点续传检查点 |
| 14 | `etl_data_coverage` | ETL表 | 数据覆盖范围 |
| 15 | `etl_backfill_task` | ETL表 | 补历史任务 |
| 16 | `etl_job_run_log` | ETL表 | 任务运行日志 |

---

## 3. 表创建顺序

脚本按依赖顺序创建表：

1. **维度表**（无依赖）：`app_user`、`dwd_security_master`、`dwd_trade_calendar`、`dwd_board_master`
2. **事实表**（依赖维度表）：`dwd_stock_daily`、`dwd_stock_adjust_factor`、`dwd_stock_financial_indicator`、`dwd_stock_factor_daily`、`dwd_board_relation`
3. **派生表**（依赖事实表）：`mart_stock_selection_daily`、`mart_user_watchlist`
4. **ETL管理表**（无依赖，可独立运行）：`etl_job_run`、`etl_checkpoint`、`etl_data_coverage`、`etl_backfill_task`、`etl_job_run_log`

---

## 4. 初始化方法

### 4.1 使用 psql 命令执行

```bash
psql -h <主机> -U <用户> -d <数据库名> -f docs/09_postgresql_ddl.sql
```

### 4.2 初始化检查

执行完成后，连接数据库验证：

```sql
-- 查看所有表
\dt

-- 预期结果：16 张表
```

### 4.3 幂等性说明

脚本使用 `create table if not exists` 和 `create index if not exists`，重复执行不会重复创建，可安全重复执行。

---

## 5. 主键与索引一览

| 表名 | 主键 | 重要索引 |
|------|------|---------|
| `app_user` | `id` | `username` (unique) |
| `dwd_security_master` | `symbol` | `(ticker, exchange)` unique |
| `dwd_trade_calendar` | `(exchange, trade_date)` | - |
| `dwd_stock_daily` | `(trade_date, symbol)` | `(symbol, trade_date desc)`, `(trade_date)` |
| `dwd_stock_adjust_factor` | `(trade_date, symbol)` | `(symbol, trade_date desc)` |
| `dwd_stock_financial_indicator` | `(symbol, report_period, report_type)` | `(report_period desc)`, `(announce_date desc)` |
| `dwd_stock_factor_daily` | `(trade_date, symbol)` | `(symbol, trade_date desc)` |
| `dwd_board_master` | `board_code` | - |
| `dwd_board_relation` | `(symbol, board_code)` | `(symbol)`, `(board_code)` |
| `mart_stock_selection_daily` | `(trade_date, symbol)` | `(symbol)`, `(trade_date)` |
| `mart_user_watchlist` | `id` | `(user_id, symbol)` unique |
| `etl_job_run` | `id` | `(job_name, biz_date)`, `(status)` |
| `etl_checkpoint` | `(job_name, checkpoint_key)` | - |
| `etl_data_coverage` | `(symbol, data_type)` | - |
| `etl_backfill_task` | `id` | `(symbol)`, `(status)`, `(created_at desc)` |
| `etl_job_run_log` | `id` | `(job_id)`, `(created_at)` |

---

## 6. 相关文档

- [数据库设计文档](stock-fast-api/docs/A股股票信息缓存系统数据库设计文档.md)
- [表关系说明](stock-fast-api/docs/A股股票信息缓存系统表关系说明文档.md)
- [部署指南](DEPLOYMENT.md)