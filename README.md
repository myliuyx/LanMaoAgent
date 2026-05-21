# A股股票信息缓存系统 
# A-Stock Information Caching System

[中文](#中文) | [English](#english)

---

## 中文

### 项目介绍

A 股股票信息缓存系统是一个 A 股本地化数据分析平台，通过 [baostock](http://www.baostock.com/) 将每日市场数据同步到本地 PostgreSQL 数据库，并提供功能完整的 Web 管理后台，支持选股分析、个股详情、板块分析、ETL 任务监控等功能。

### 核心功能

- **盘后数据同步** — 自动同步全市场行情、财务指标、技术因子
- **智能选股** — 按技术指标（均线、RSI、MACD、ATR）和财务指标（ROE、营收、市盈率）筛选
- **个股分析** — K线图、历史行情、技术指标、财务数据、所属板块
- **板块分析** — 行业板块、概念板块、成分股查询
- **ETL 任务监控** — 实时任务状态、手动触发、执行日志
- **数据回补** — 支持个股历史数据补充
- **数据覆盖追踪** — 监控个股历史数据完整性

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (Vue 3)                            │
│   控制台 │ 选股 │ 个股详情 │ 板块 │ 任务监控                     │
└────────────────────────────┬────────────────────────────────┘
                             │ REST API (/api/v1)
┌────────────────────────────▼────────────────────────────────┐
│                   后端 (FastAPI)                             │
│  Router → Schema → Service → Repository                     │
│  APScheduler 定时任务 (工作日 18:00-21:30)                    │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│              PostgreSQL (13张表，约630万行)                  │
│  dwd_stock_daily │ dwd_stock_factor_daily │ mart_selection  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                       数据来源                               │
│                     baostock.com                            │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3, TypeScript, Vite, Element Plus, ECharts, lightweight-charts |
| 后端 | FastAPI, SQLAlchemy, APScheduler, Pydantic |
| 数据库 | PostgreSQL 15+ |
| 数据源 | baostock, efinance |

### 快速开始

#### 方式一：Docker Compose（推荐）

```bash
git clone https://github.com/myliuyx/stock_project.git
cd stock_project/stock-fast-api

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库和 JWT 配置

# 启动后端服务
docker-compose up -d

# 前端（独立部署）
cd ../stock-front_ui
docker build -t stock-frontend .
docker run -d -p 5173:80 --name stock-frontend stock-frontend
```

#### 方式二：手动部署

**后端：**

```bash
cd stock-fast-api

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库和 JWT 配置

# 初始化数据库
psql -h <host> -U <user> -d <dbname> -f docs/09_postgresql_ddl.sql

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端：**

```bash
cd stock-front_ui

npm install

npm run dev
# 访问 http://localhost:5173
```

### 环境变量说明

**后端 (`stock-fast-api/.env`)：**

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `DB_HOST` | 是 | - | PostgreSQL 主机地址 |
| `DB_PORT` | 否 | 5432 | PostgreSQL 端口 |
| `DB_NAME` | 是 | - | 数据库名 |
| `DB_USER` | 是 | - | 数据库用户 |
| `DB_PASSWORD` | 是 | - | 数据库密码 |
| `JWT_SECRET_KEY` | 是 | - | JWT 签名密钥（至少32字符） |
| `CORS_ORIGINS` | 否 | - | 允许的跨域地址（逗号分隔） |

### 项目结构

```
stock_project/
├── stock-fast-api/          # FastAPI 后端
│   ├── app/
│   │   ├── core/            # 配置、数据库、异常、响应封装
│   │   ├── routers/         # API 路由模块（10个文件，42个端点）
│   │   ├── schemas/         # Pydantic 数据模型
│   │   ├── services/        # 业务逻辑（10个服务）
│   │   ├── repositories/    # 数据访问层（6个仓库）
│   │   └── jobs/            # ETL 任务脚本（10个任务）
│   ├── docs/                # API 文档、数据库设计、架构文档
│   └── docker-compose.yml   # Docker 部署配置
│
└── stock-front_ui/          # Vue 3 前端
    ├── src/
    │   ├── api/             # Axios 请求层
    │   ├── components/      # 按模块分类的 Vue 组件
    │   ├── pages/           # 路由页面组件
    │   ├── stores/          # Pinia 状态管理
    │   └── layouts/         # 主布局组件
    └── nginx.conf           # Nginx 配置
```

### 数据库表

| 表名 | 记录数（约） | 说明 |
|------|-------------|------|
| `dwd_security_master` | 5,198 | 股票主数据（代码、名称、交易所、行业） |
| `dwd_stock_daily` | 487万 | 日线行情数据 |
| `dwd_stock_financial_indicator` | 35,811 | 财务指标 |
| `dwd_stock_adjust_factor` | 33,948 | 复权因子 |
| `dwd_board_master` | 83 | 板块定义 |
| `dwd_board_relation` | 5,199 | 股票-板块关系 |
| `dwd_stock_factor_daily` | 127万 | 技术指标（均线、RSI、MACD、ATR） |
| `mart_stock_selection_daily` | 62万 | 选股宽表 |
| `etl_job_run` | 934+ | ETL 任务执行记录 |

### API 文档

API 前缀：`/api/v1`

| 模块 | 端点数 | 说明 |
|------|--------|------|
| Auth | 2 | 登录、Token 验证 |
| Dashboard | 4 | 系统概览、任务状态 |
| Selection | 5 | 选股查询、导出 |
| Stocks | 9 | 行情搜索、个股资料、日线、技术因子、财务数据 |
| Jobs | 9 | 任务列表、触发、取消、日志 |
| Coverage | 3 | 数据覆盖概览 |
| Boards | 3 | 板块列表、板块详情、成分股 |
| Backfill | 2 | 历史数据回补 |
| Watchlist | 4 | 自选股管理 |

完整 API 文档：[`stock-fast-api/docs/REGISTRY.md`](stock-fast-api/docs/REGISTRY.md)

### 定时任务

> 详细配置见 [定时任务使用文档](stock-fast-api/docs/定时任务使用文档.md)

时间均为北京时间（UTC+8）：

| 任务ID | 执行时间 | 说明 |
|--------|----------|------|
| `security_master_sync` | 工作日 18:00 | 同步股票主数据 |
| `daily_stock_sync` | 工作日 19:00 | 同步日线行情 |
| `factor_compute` | 工作日 20:30 | 计算技术指标 |
| `selection_mart` | 工作日 21:30 | 构建选股宽表 |
| `cleanup_logs` | 每日 00:05 | 清理超过3天的日志 |

### 相关文档

- [快速入门指南](docs/QUICK_START.md)
- [用户使用指南](docs/USER_GUIDE.md)
- [Docker 部署详解](docs/DEPLOYMENT.md)
- [API 接口文档](stock-fast-api/docs/REGISTRY.md)
- [数据库设计文档](stock-fast-api/docs/A股股票信息缓存系统数据库设计文档.md)
- [架构设计文档](stock-fast-api/docs/A股股票信息缓存系统架构设计文档.md)

### 许可证

MIT License

---

## English

### Overview

A-Stock Information Caching System is a local data analysis platform for China's A-share market (A股). It synchronizes daily market data from [baostock](http://www.baostock.com/) into a local PostgreSQL database and provides a full-featured web dashboard for stock screening, individual stock analysis, sector analysis, and ETL job monitoring.

### Features

- **Daily Data Sync** — Automatic synchronization of full-market OHLCV data, financial indicators, and technical factors after market close
- **Smart Stock Screening** — Filter stocks by technical indicators (MA, RSI, MACD, ATR) and financial metrics (ROE, revenue, P/E)
- **Individual Stock Analysis** — K-line charts, historical prices, technical factors, financial data, and board membership
- **Sector/Board Analysis** — Industry boards, concept boards, and member stocks
- **ETL Job Monitoring** — Real-time task status, manual triggering, execution logs
- **Historical Data Backfill** — Supplement missing data for individual stocks
- **Data Coverage Tracking** — Monitor historical data completeness per stock

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3)                       │
│   Dashboard │ Selection │ Stock Detail │ Boards │ Jobs      │
└────────────────────────────┬────────────────────────────────┘
                             │ REST API (/api/v1)
┌────────────────────────────▼────────────────────────────────┐
│                   Backend (FastAPI)                         │
│  Router → Schema → Service → Repository                     │
│  APScheduler (Daily 18:00-21:30 Beijing Time)              │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│              PostgreSQL (13 tables, ~6.3M rows)             │
│  dwd_stock_daily │ dwd_stock_factor_daily │ mart_selection  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                     Data Source                             │
│                   baostock.com                              │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Vue 3, TypeScript, Vite, Element Plus, ECharts, lightweight-charts |
| Backend | FastAPI, SQLAlchemy, APScheduler, Pydantic |
| Database | PostgreSQL 15+ |
| Data Source | baostock, efinance |

### Quick Start

#### Option 1: Docker Compose (Recommended)

```bash
git clone https://github.com/myliuyx/stock_project.git
cd stock_project/stock-fast-api

# Configure environment
cp .env.example .env
# Edit .env with your database and JWT settings

# Start services
docker-compose up -d

# Frontend (separate)
cd ../stock-front_ui
docker build -t stock-frontend .
docker run -d -p 5173:80 --name stock-frontend stock-frontend
```

#### Option 2: Manual Setup

**Backend:**

```bash
cd stock-fast-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database and JWT settings

# Initialize database
psql -h <host> -U <user> -d <dbname> -f docs/09_postgresql_ddl.sql

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**

```bash
cd stock-front_ui

npm install

npm run dev
# Visit http://localhost:5173
```

### Environment Variables

**Backend (`stock-fast-api/.env`):**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_HOST` | Yes | - | PostgreSQL host |
| `DB_PORT` | No | 5432 | PostgreSQL port |
| `DB_NAME` | Yes | - | Database name |
| `DB_USER` | Yes | - | Database user |
| `DB_PASSWORD` | Yes | - | Database password |
| `JWT_SECRET_KEY` | Yes | - | JWT signing key (min 32 chars) |
| `CORS_ORIGINS` | No | - | Allowed CORS origins (comma-separated) |

### Project Structure

```
stock_project/
├── stock-fast-api/          # FastAPI backend
│   ├── app/
│   │   ├── core/            # Config, database, exceptions, response
│   │   ├── routers/         # API route modules (10 files, 42 endpoints)
│   │   ├── schemas/         # Pydantic DTOs
│   │   ├── services/        # Business logic (10 services)
│   │   ├── repositories/    # Data access (6 repositories)
│   │   └── jobs/            # ETL job scripts (10 jobs)
│   ├── docs/                # API registry, DB design, architecture docs
│   └── docker-compose.yml   # Docker deployment
│
└── stock-front_ui/          # Vue 3 frontend
    ├── src/
    │   ├── api/             # Axios API layer
    │   ├── components/      # Vue components by module
    │   ├── pages/           # Route page components
    │   ├── stores/          # Pinia state management
    │   └── layouts/         # Main layout
    └── nginx.conf           # Nginx configuration
```

### Database Tables

| Table | Rows (approx.) | Description |
|-------|---------------|-------------|
| `dwd_security_master` | 5,198 | Stock master data (symbol, name, exchange, industry) |
| `dwd_stock_daily` | 4.87M | Daily OHLCV data |
| `dwd_stock_financial_indicator` | 35,811 | Financial indicators |
| `dwd_stock_adjust_factor` | 33,948 | Price adjustment factors |
| `dwd_board_master` | 83 | Board/sector definitions |
| `dwd_board_relation` | 5,199 | Stock-board relationships |
| `dwd_stock_factor_daily` | 1.27M | Technical factors (MA, RSI, MACD, ATR) |
| `mart_stock_selection_daily` | 621,491 | Stock selection wide table |
| `etl_job_run` | 934+ | ETL job execution records |

### API Documentation

API base URL: `/api/v1`

| Module | Endpoints | Description |
|--------|-----------|-------------|
| Auth | 2 | Login, token verification |
| Dashboard | 4 | System overview, task summary |
| Selection | 5 | Stock screening, export |
| Stocks | 9 | Quote search, profile, daily, factors, finance |
| Jobs | 9 | Task list, trigger, cancel, logs |
| Coverage | 3 | Data coverage overview |
| Boards | 3 | Board list, detail, members |
| Backfill | 2 | Historical data backfill |
| Watchlist | 4 | User watchlist management |

Full API documentation: [`stock-fast-api/docs/REGISTRY.md`](stock-fast-api/docs/REGISTRY.md)

### Scheduled Tasks

All times in Beijing time (UTC+8):

| Task ID | Schedule | Description |
|---------|----------|-------------|
| `security_master_sync` | Mon-Fri 18:00 | Sync stock master data |
| `daily_stock_sync` | Mon-Fri 19:00 | Sync daily OHLCV |
| `factor_compute` | Mon-Fri 20:30 | Compute technical factors |
| `selection_mart` | Mon-Fri 21:30 | Build stock selection mart |
| `cleanup_logs` | Daily 00:05 | Clean old logs (>3 days) |

### Related Documents

- [Quick Start Guide](docs/QUICK_START.md)
- [User Guide](docs/USER_GUIDE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [API Registry](stock-fast-api/docs/REGISTRY.md)
- [Database Design](stock-fast-api/docs/A股股票信息缓存系统数据库设计文档.md)
- [Architecture Design](stock-fast-api/docs/A股股票信息缓存系统架构设计文档.md)

### License

MIT License