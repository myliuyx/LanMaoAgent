# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

A股股票信息缓存系统 FastAPI 后端，基于 **FastAPI + SQLAlchemy + PostgreSQL**，采用 Router → Schema → Service → Repository 分层架构。

## 常用命令

```bash
# 安装依赖
./venv/bin/pip install -r requirements.txt

# 语法检查
python -m py_compile app/repositories/xxx.py

# 启动测试服务
./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8081

# 运行测试
./venv/bin/pytest

# 运行单个测试文件
./venv/bin/pytest tests/ -v

# Docker 构建
docker build -t stock-api .
```

## 架构概览

```
Router 层   →  接收请求 / 调用 Service / 返回统一响应  (routers/)
Schema 层   →  请求模型 / 响应模型 / 参数校验           (schemas/)
Service 层  →  业务逻辑 / 数据聚合 / 流程控制           (services/)
Repository  →  数据库交互 / SQL 编写                     (repositories/)
Utils 层    →  分页构建 / 参数校验 / 通用工具           (utils/)
Core 层     →  配置 / 数据库连接 / 异常 / 响应封装      (core/)
```

## 统一规范

- **API 前缀**: `/api/v1`
- **响应结构**: `{"code": 0, "message": "success", "data": {...}}`
- **分页结构**: `{"list": [...], "page": 1, "page_size": 20, "total": N}`
- **错误码**: 定义在 `app/core/exceptions.py`
- **数据库访问**: 使用 SQLAlchemy `text()` 原始 SQL 查询，不使用 ORM

## 关键文件索引

| 文件 | 用途 |
|------|------|
| `app/main.py` | 启动入口，路由注册，全局异常处理，定时任务调度器 |
| `app/core/config.py` | 配置管理（数据库、JWT） |
| `app/core/deps.py` | 依赖注入（get_db, get_current_user） |
| `app/core/exceptions.py` | 业务异常类（BizException, NotFoundException） |
| `app/core/response.py` | 统一响应封装 |
| `app/scheduler.py` | 定时任务调度器 |

## 数据库表（实测状态）

| 表名 | 记录数 | 说明 |
|------|--------|------|
| `dwd_security_master` | 5,198 | ✅ 有数据 |
| `dwd_stock_daily` | 4,865,714 | ✅ 有数据 |
| `dwd_trade_calendar` | 4,382 | ✅ 有数据 |
| `dwd_stock_financial_indicator` | 35,811 | ✅ 有数据 |
| `etl_job_run` | 934+ | ✅ 有数据 |
| `dwd_stock_adjust_factor` | 33,948 | ✅ 有数据 |
| `dwd_board_master` | 83 | ✅ 有数据 |
| `dwd_board_relation` | 5,199 | ✅ 有数据 |
| `dwd_stock_factor_daily` | 1,267,428 | ✅ 有数据 |
| `mart_stock_selection_daily` | 621,491 | ✅ 有数据 |
| `mart_user_watchlist` | — | 用户自选股 |
| `etl_checkpoint` | — | 断点续传 |
| `etl_data_coverage` | — | 数据覆盖 |
| `etl_backfill_task` | — | 补历史任务 |
| `etl_job_run_log` | — | 任务日志 |
| `app_user` | — | 用户认证 |

## API 路由模块

| 模块 | 路径前缀 | 说明 |
|------|---------|------|
| auth | `/api/v1/auth` | 认证 |
| dashboard | `/api/v1/dashboard` | 仪表盘 |
| selection | `/api/v1/selection` | 选股 |
| stocks | `/api/v1/stocks` | 股票行情 |
| jobs | `/api/v1/jobs` | ETL 任务 |
| coverage | `/api/v1/coverage` | 数据覆盖 |
| boards | `/api/v1/boards` | 板块 |
| backfill | `/api/v1/backfill` | 回填 |
| system | `/api/v1/system` | 系统 |
| watchlist | `/api/v1/watchlist` | 自选股 |

## 开发流程

### 任务分类

| 类型 | 描述 | 处理方式 |
|------|------|---------|
| A类 | Mock 接口改为真实 SQL | 走完整流程 |
| B类 | 新增接口（前后端约定后从零开发）| 走完整流程 |
| C类 | Bug 修复 | 跳过技术设计，快速定位修复 |
| D类 | 数据库变更（新建表/字段/索引）| 数据库先行 |
| E类 | ETL 脚本修改 | 独立流程 |
| F类 | 文档维护 | 轻量流程 |

### 自测三连

```bash
# 1. 语法检查
python -m py_compile app/repositories/xxx.py

# 2. 启动测试服务
./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8081

# 3. 验证
curl http://localhost:8081/api/v1/stocks/search?keyword=茅台
```

## 新增/修改接口

1. 按 **Schema → Repository → Service → Router** 顺序开发
2. Repository 使用 `text()` 包装原始 SQL，通过 `self.db.execute(text(sql), params)` 执行
3. 如目标表无数据，保留 Mock 并加 `// TODO` 注释标注真实 SQL
4. 自测通过后提交

## 文档索引

| 文档 | 说明 |
|------|------|
| [REGISTRY.md](docs/REGISTRY.md) | **完整 API 文档**（42端点）— 权威来源 |
| [数据库设计文档](docs/A股股票信息缓存系统数据库设计文档.md) | 数据库表结构设计（完整，已补全） |
| [架构设计文档](docs/A股股票信息缓存系统架构设计文档.md) | 系统架构与数据流 |
| [表关系说明](docs/A股股票信息缓存系统表关系说明文档.md) | 表之间关联关系 |
| [定时任务使用文档](docs/定时任务使用文档.md) | ETL 任务配置管理 |
| [DDL 脚本](../docs/09_postgresql_ddl.sql) | 数据库建表脚本（16张表） |
| [DDL 参考](../docs/DDL_REFERENCE.md) | DDL 脚本使用说明 |
