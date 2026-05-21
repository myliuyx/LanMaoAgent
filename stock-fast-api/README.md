# A股股票信息缓存系统 - FastAPI 后端 / FastAPI Backend

[English](#english) | [中文](#中文)

---

## English

### Overview

FastAPI backend for the A-Stock Information Caching System. Provides a REST API (`/api/v1`) for stock data queries, screening, and ETL job management.

### Tech Stack

- **Framework**: FastAPI + Uvicorn
- **ORM**: SQLAlchemy (raw SQL via `text()`)
- **Database**: PostgreSQL 15+
- **Scheduler**: APScheduler
- **Authentication**: JWT (Bearer token)
- **Data Source**: baostock, efinance

### Requirements

- Python 3.10+
- PostgreSQL 15+
- 2GB+ RAM recommended

### Quick Start

```bash
# Enter backend directory
cd stock-fast-api

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database and JWT settings

# Initialize database (requires PostgreSQL running)
psql -h <host> -U <user> -d <dbname> -f docs/09_postgresql_ddl.sql

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API documentation available at http://localhost:8000/docs
```

### Environment Variables

Create a `.env` file in `stock-fast-api/`:

| Variable | Required | Description |
|----------|----------|-------------|
| `DB_HOST` | Yes | PostgreSQL host |
| `DB_PORT` | No | PostgreSQL port (default: 5432) |
| `DB_NAME` | Yes | Database name |
| `DB_USER` | Yes | Database user |
| `DB_PASSWORD` | Yes | Database password |
| `JWT_SECRET_KEY` | Yes | JWT signing key (min 32 characters) |
| `CORS_ORIGINS` | No | Allowed CORS origins (comma-separated) |

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# The API will be available at http://localhost:8000
```

### Architecture

```
app/
├── main.py              # App entry, route registration, scheduler
├── core/                # Config, database, exceptions, response
├── routers/            # API route handlers (10 modules)
├── schemas/            # Pydantic DTOs
├── services/           # Business logic (10 services)
├── repositories/       # Data access (6 repositories)
├── jobs/               # ETL job scripts (10 jobs)
└── utils/              # Pagination, validation utilities
```

### API Modules

| Module | Prefix | Endpoints |
|--------|--------|-----------|
| Auth | `/api/v1/auth` | login, verify |
| Dashboard | `/api/v1/dashboard` | summary, jobs, coverage, watchlist-analysis |
| Selection | `/api/v1/selection` | dates, industries, top, query, export |
| Stocks | `/api/v1/stocks` | search, profile, daily, factors, finance, adjust-factor, boards, latest |
| Jobs | `/api/v1/jobs` | list, run, sync-daily, sync-financial, sync-factor, sync-selection, detail, logs, cancel |
| Coverage | `/api/v1/coverage` | list, summary, detail |
| Boards | `/api/v1/boards` | list, detail, members |
| Backfill | `/api/v1/backfill` | run, status |
| System | `/api/v1/system` | meta |
| Watchlist | `/api/v1/watchlist` | list, add, delete, check |

### Response Format

```json
// Success
{"code": 0, "message": "success", "data": {...}}

// Paginated
{"list": [...], "page": 1, "page_size": 20, "total": N}
```

### Scheduled Tasks

| Task ID | Schedule (Beijing Time) | Description |
|---------|------------------------|-------------|
| `security_master_sync` | Mon-Fri 18:00 | Sync stock master data |
| `daily_stock_sync` | Mon-Fri 19:00 | Sync daily OHLCV |
| `factor_compute` | Mon-Fri 20:30 | Compute technical factors |
| `selection_mart` | Mon-Fri 21:30 | Build stock selection mart |
| `cleanup_logs` | Daily 00:05 | Clean old logs |

### Documentation

- [API Registry](docs/REGISTRY.md) — Complete API documentation with examples
- [Database Design](docs/A股股票信息缓存系统数据库设计文档.md)
- [Architecture Design](docs/A股股票信息缓存系统架构设计文档.md)
- [Scheduled Tasks Guide](docs/定时任务使用文档.md)
- [Database DDL](docs/09_postgresql_ddl.sql)

---

## 中文

### 概述

A 股股票信息缓存系统的 FastAPI 后端，提供 REST API（`/api/v1`），用于股票数据查询、选股筛选和 ETL 任务管理。

### 技术栈

- **框架**: FastAPI + Uvicorn
- **ORM**: SQLAlchemy（使用 `text()` 原始 SQL）
- **数据库**: PostgreSQL 15+
- **调度器**: APScheduler
- **认证**: JWT（Bearer token）
- **数据源**: baostock, efinance

### 环境要求

- Python 3.10+
- PostgreSQL 15+
- 推荐 2GB+ 内存

### 快速开始

```bash
# 进入后端目录
cd stock-fast-api

# 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库和 JWT 配置

# 初始化数据库（需要先启动 PostgreSQL）
psql -h <host> -U <user> -d <dbname> -f docs/09_postgresql_ddl.sql

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API 文档: http://localhost:8000/docs
```

### 环境变量

在 `stock-fast-api/` 目录创建 `.env` 文件：

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `DB_HOST` | 是 | PostgreSQL 主机地址 |
| `DB_PORT` | 否 | PostgreSQL 端口（默认 5432） |
| `DB_NAME` | 是 | 数据库名 |
| `DB_USER` | 是 | 数据库用户 |
| `DB_PASSWORD` | 是 | 数据库密码 |
| `JWT_SECRET_KEY` | 是 | JWT 签名密钥（至少 32 字符） |
| `CORS_ORIGINS` | 否 | 允许的跨域地址（逗号分隔） |

### Docker 部署

```bash
# 构建并启动
docker-compose up -d

# API 地址: http://localhost:8000
```

### 架构

```
app/
├── main.py              # 应用入口、路由注册、定时任务调度
├── core/                # 配置、数据库连接、异常、响应封装
├── routers/             # API 路由处理（10 个模块）
├── schemas/             # Pydantic 数据模型
├── services/            # 业务逻辑（10 个服务）
├── repositories/        # 数据访问层（6 个仓库）
├── jobs/                # ETL 任务脚本（10 个任务）
└── utils/               # 分页、校验等工具
```

### API 模块

| 模块 | 前缀 | 端点 |
|------|------|------|
| Auth | `/api/v1/auth` | 登录、Token 验证 |
| Dashboard | `/api/v1/dashboard` | 概览、任务状态、覆盖、自选股分析 |
| Selection | `/api/v1/selection` | 选股、交易日列表、导出 |
| Stocks | `/api/v1/stocks` | 搜索、资料、日线、技术因子、财务、复权因子、板块、最新价 |
| Jobs | `/api/v1/jobs` | 列表、触发、同步日线、同步财务、同步因子、同步选股、详情、日志、取消 |
| Coverage | `/api/v1/coverage` | 列表、概览、详情 |
| Boards | `/api/v1/boards` | 列表、详情、成分股 |
| Backfill | `/api/v1/backfill` | 执行、状态 |
| System | `/api/v1/system` | 元信息 |
| Watchlist | `/api/v1/watchlist` | 列表、添加、删除、检查 |

### 响应格式

```json
// 成功响应
{"code": 0, "message": "success", "data": {...}}

// 分页响应
{"list": [...], "page": 1, "page_size": 20, "total": N}
```

### 定时任务

| 任务 ID | 执行时间（北京时间） | 说明 |
|---------|---------------------|------|
| `security_master_sync` | 工作日 18:00 | 同步股票主数据 |
| `daily_stock_sync` | 工作日 19:00 | 同步日线行情 |
| `factor_compute` | 工作日 20:30 | 计算技术指标 |
| `selection_mart` | 工作日 21:30 | 构建选股宽表 |
| `cleanup_logs` | 每日 00:05 | 清理超过3天的日志 |

### 文档

- [API 接口文档](docs/REGISTRY.md) — 完整的 API 文档（含请求/响应示例）
- [数据库设计文档](docs/A股股票信息缓存系统数据库设计文档.md)
- [架构设计文档](docs/A股股票信息缓存系统架构设计文档.md)
- [定时任务使用文档](docs/定时任务使用文档.md)
- [数据库 DDL](docs/09_postgresql_ddl.sql)