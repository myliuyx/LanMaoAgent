# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a monorepo containing the **A股股票信息缓存系统** (A-Stock Information Caching System):

- `stock-fast-api/` — FastAPI backend (PostgreSQL + SQLAlchemy)
- `stock-front_ui/` — Vue 3 + TypeScript frontend (Element Plus, ECharts)

**Architecture**: Backend serves a REST API (`/api/v1/*`) consumed by the frontend. The backend handles database queries; the frontend provides the admin dashboard, stock screening console, and operations monitoring UI.

## Quick Commands

### Backend
```bash
cd stock-fast-api
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8081
./venv/bin/pytest                          # run tests
./venv/bin/pytest tests/ -v               # run single test file
```

### Frontend
```bash
cd stock-front_ui
npm install
npm run dev                               # dev server on :5173 (proxies /api to 192.168.3.18:8000)
npm run build
```

## Repository Structure

```
stock_project/
├── stock-fast-api/          # FastAPI backend (Router → Schema → Service → Repository)
│   ├── app/
│   │   ├── core/            # config, db, exceptions, response
│   │   ├── routers/         # 9 API route modules (31 endpoints)
│   │   ├── schemas/         # Pydantic DTOs
│   │   ├── services/        # 8 business services
│   │   ├── repositories/    # 7 data access repositories
│   │   ├── utils/           # pagination, validation
│   │   └── scheduler.py     # scheduled task runner
│   └── docs/                # API registry, DB design docs
└── stock-front_ui/           # Vue 3 frontend
    ├── src/
    │   ├── api/             # Axios layer (request.ts + domain modules)
    │   ├── components/      # base/, stock/, selection/, job/, board/
    │   ├── pages/           # route page components
    │   ├── stores/          # Pinia stores (app, tradeDate, job, selectionTemplate)
    │   └── layouts/         # MainLayout.vue
    └── mock/                # mock data for development
```

## Key Conventions

- **API prefix**: `/api/v1`
- **Response format**: `{"code": 0, "message": "success", "data": {...}}`
- **Pagination format**: `{"list": [...], "page": 1, "page_size": 20, "total": N}`
- **Auth**: Bearer token in `Authorization` header; 401 → redirect to `/login`
- **Job polling**: frontend polls `/api/v1/jobs?status=RUNNING` every 10s for task status
- **Backend DB access**: raw SQL via `sqlalchemy.text()`, no ORM
- **Error codes**: defined in `app/core/exceptions.py`

## Development Workflow

### Task Types

| Type | Description | Approach |
|------|-------------|----------|
| A类 | Mock 接口改为真实 SQL | Full flow (Schema → Repo → Service → Router) |
| B类 | 新增接口 | Full flow from scratch |
| C类 | Bug 修复 | Skip design doc, quick fix |
| D类 | 数据库变更 | Database-first |
| E类 | ETL 脚本修改 | Independent process |
| F类 | 文档维护 | Lightweight |

### Backend Self-Test Three-Step

```bash
# 1. Syntax check
python -m py_compile app/repositories/xxx.py

# 2. Start test server
./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8081

# 3. curl the endpoint
curl http://localhost:8081/api/v1/stocks/search?keyword=茅台
```

## Adding/Modifying Backend APIs

Follow the **Schema → Repository → Service → Router** order:

1. Define request/response Pydantic models in `schemas/`
2. Write the SQL query in `repositories/` using `text(sql)` + `db.execute(text(sql), params)`
3. Implement business logic in `services/`
4. Wire up the route in `routers/`
5. Self-test: syntax check → start server → `curl` the endpoint

## Detailed Documentation

Each sub-project has its own CLAUDE.md with complete details:
- Backend specifics → `stock-fast-api/CLAUDE.md`
- Frontend specifics → `stock-front_ui/CLAUDE.md`

## Documentation Index

All project documentation lives in `docs/` (root-level user/ops docs) and each sub-project's `docs/` folder (technical reference docs).

**文档层级结构**：

```
一级 — 快速开始
├── docs/QUICK_START.md          首次安装部署
└── docs/DEPLOYMENT.md           Docker 部署详解

二级 — 用户指南
├── docs/USER_GUIDE.md           功能使用方法
└── docs/TROUBLESHOOTING.md      常见问题与解决方案

三级 — 参考文档
├── stock-fast-api/docs/REGISTRY.md                             # API 完整文档（42端点）— 权威来源
├── stock-fast-api/docs/A股股票信息缓存系统数据库设计文档.md  # 数据库表结构
├── stock-fast-api/docs/A股股票信息缓存系统表关系说明文档.md  # 表之间关联
├── stock-fast-api/docs/A股股票信息缓存系统架构设计文档.md    # 系统架构与数据流
└── stock-front_ui/docs/A股股票信息缓存系统前后端API接口设计文档.md  # 前端视角 API 速查

四级 — 运维指南
├── docs/DDL_REFERENCE.md                                        # 数据库 DDL 脚本说明
└── stock-fast-api/docs/定时任务使用文档.md                      # ETL 任务配置管理
```

**文档导航入口**：`docs/README.md` — 包含所有文档的层级索引和快速链接。
