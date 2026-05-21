# A股股票信息缓存系统 - 前端项目 / Vue 3 Frontend

[English](#english) | [中文](#中文)

---

## English

### Overview

Vue 3 + TypeScript frontend for the A-Stock Information Caching System. Provides a web dashboard for stock screening, individual stock analysis, sector analysis, and ETL job monitoring.

### Tech Stack

- **Framework**: Vue 3.5 + TypeScript 5
- **Build Tool**: Vite 6
- **UI Library**: Element Plus 2.9
- **State Management**: Pinia 3.0
- **Routing**: Vue Router 4.5
- **HTTP Client**: Axios 1.9
- **Charts**: ECharts 5.6, lightweight-charts 4.2 (K-line)

### Requirements

- Node.js 18+

### Quick Start

```bash
# Enter frontend directory
cd stock-front_ui

# Install dependencies
npm install

# Start development server
npm run dev
# Visit http://localhost:5173
```

### Environment Variables

Create a `.env` file in `stock-front_ui/`:

```bash
VITE_API_BASE_URL=/api/v1    # API base path (uses Vite proxy in dev)
```

In development, the Vite dev server proxies `/api` to the backend (default: `http://localhost:8000`). Configure proxy in `vite.config.ts`.

### Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

### Docker Deployment

```bash
# Build
docker build -t stock-frontend .

# Run
docker run -d -p 5173:80 --name stock-frontend stock-frontend
```

### Project Structure

```
src/
├── api/                     # Axios API layer
│   ├── request.ts           # Axios instance with interceptors
│   ├── auth.ts              # Authentication
│   ├── dashboard.ts         # Dashboard
│   ├── selection.ts         # Stock screening
│   ├── stock.ts             # Stock details
│   ├── board.ts             # Board/sector
│   ├── job.ts               # ETL jobs
│   ├── coverage.ts          # Data coverage
│   ├── backfill.ts          # Backfill
│   └── watchlist.ts         # Watchlist
│
├── components/              # Vue components by module
│   ├── base/                # Base components (BaseChart, BaseDrawer, etc.)
│   ├── dashboard/           # Dashboard components
│   ├── selection/           # Selection components (FilterPanel, ResultTable)
│   ├── stock/               # Stock components (KLineChart, VolumeChart)
│   ├── board/               # Board components
│   └── job/                 # Job components (JobLogViewer)
│
├── pages/                   # Route page components
│   ├── DashboardPage.vue    # System overview
│   ├── SelectionPage.vue    # Stock screening workstation
│   ├── StockDetailPage.vue  # Individual stock analysis
│   ├── BoardListPage.vue    # Board list
│   ├── BoardDetailPage.vue  # Board detail
│   ├── JobListPage.vue      # Job list
│   ├── JobDetailPage.vue    # Job detail and logs
│   ├── CoveragePage.vue     # Data coverage
│   ├── BackfillPage.vue     # Historical backfill
│   ├── WatchlistPage.vue    # User watchlist
│   ├── SettingsPage.vue     # System settings
│   └── LoginPage.vue        # Login
│
├── layouts/                 # Layout components
│   └── MainLayout.vue       # Sidebar + top bar + content
│
├── stores/                  # Pinia stores
│   ├── app.ts               # Token, user info, auth state
│   ├── tradeDate.ts         # Current trading day
│   ├── job.ts               # Job list, 10s polling
│   └── selectionTemplate.ts # Screening templates
│
├── types/                   # TypeScript type definitions
├── utils/                   # Utility functions
├── router/                  # Vue Router config
├── App.vue                  # Root component
└── main.ts                  # Entry point
```

### Pages & Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | → `/dashboard` | Redirect |
| `/login` | LoginPage | Login |
| `/dashboard` | DashboardPage | System overview, stats |
| `/selection` | SelectionPage | Stock screening workstation |
| `/stocks/:symbol` | StockDetailPage | Individual stock detail |
| `/boards` | BoardListPage | Sector/board list |
| `/boards/:boardCode` | BoardDetailPage | Sector detail |
| `/jobs` | JobListPage | ETL job management |
| `/jobs/:jobId` | JobDetailPage | Job detail & logs |
| `/coverage` | CoveragePage | Data coverage overview |
| `/backfill` | BackfillPage | Historical backfill |
| `/watchlist` | WatchlistPage | User watchlist |
| `/settings` | SettingsPage | System settings |

### Authentication

- JWT Bearer token stored in `localStorage`
- Token injected in all API requests via Axios interceptor
- 401 responses clear token and redirect to `/login`

### Key Patterns

1. **API Layer**: Unified Axios instance in `request.ts` with error handling
2. **Job Polling**: `JobStore` polls `/api/v1/jobs?status=RUNNING` every 10 seconds
3. **K-line Charts**: Using `lightweight-charts` (TradingView)
4. **Virtual Scrolling**: `vue-virtual-scroller` for large tables (>500 rows)
5. **Build**: TypeScript strict mode; `vue-tsc -b` runs before `vite build`

### Documentation

- [Frontend Architecture Design](docs/A股股票信息缓存系统前端架构设计文档.md)
- [API Interface Design](docs/A股股票信息缓存系统前后端API接口设计文档.md)

---

## 中文

### 概述

A 股股票信息缓存系统的 Vue 3 + TypeScript 前端，提供股票筛选、个股分析、板块分析、ETL 任务监控等功能的管理后台。

### 技术栈

- **框架**: Vue 3.5 + TypeScript 5
- **构建工具**: Vite 6
- **UI 组件库**: Element Plus 2.9
- **状态管理**: Pinia 3.0
- **路由**: Vue Router 4.5
- **HTTP 客户端**: Axios 1.9
- **图表**: ECharts 5.6, lightweight-charts 4.2（K 线图）

### 环境要求

- Node.js 18+

### 快速开始

```bash
# 进入前端目录
cd stock-front_ui

# 安装依赖
npm install

# 启动开发服务器
npm run dev
# 访问 http://localhost:5173
```

### 环境变量

在 `stock-front_ui/` 目录创建 `.env` 文件：

```bash
VITE_API_BASE_URL=/api/v1    # API 基础路径（开发环境使用代理）
```

开发环境下，Vite 会将 `/api` 请求代理到后端（默认：`http://localhost:8000`）。代理配置在 `vite.config.ts` 中。

### 构建

```bash
# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

### Docker 部署

```bash
# 构建镜像
docker build -t stock-frontend .

# 运行容器
docker run -d -p 5173:80 --name stock-frontend stock-frontend
```

### 项目结构

```
src/
├── api/                     # Axios API 层
│   ├── request.ts           # Axios 实例（拦截器）
│   ├── auth.ts              # 认证
│   ├── dashboard.ts         # 仪表盘
│   ├── selection.ts         # 选股
│   ├── stock.ts             # 个股
│   ├── board.ts             # 板块
│   ├── job.ts               # ETL 任务
│   ├── coverage.ts          # 数据覆盖
│   ├── backfill.ts          # 回补
│   └── watchlist.ts         # 自选股
│
├── components/              # 按模块分类的 Vue 组件
│   ├── base/                # 基础组件（BaseChart, BaseDrawer 等）
│   ├── dashboard/           # 仪表盘组件
│   ├── selection/           # 选股组件（FilterPanel, ResultTable）
│   ├── stock/               # 个股组件（KLineChart, VolumeChart）
│   ├── board/               # 板块组件
│   └── job/                 # 任务组件（JobLogViewer）
│
├── pages/                   # 路由页面组件
│   ├── DashboardPage.vue    # 系统概览
│   ├── SelectionPage.vue    # 选股工作台
│   ├── StockDetailPage.vue  # 个股详情
│   ├── BoardListPage.vue    # 板块列表
│   ├── BoardDetailPage.vue  # 板块详情
│   ├── JobListPage.vue      # 任务列表
│   ├── JobDetailPage.vue    # 任务详情和日志
│   ├── CoveragePage.vue     # 数据覆盖
│   ├── BackfillPage.vue     # 历史回补
│   ├── WatchlistPage.vue    # 自选股
│   ├── SettingsPage.vue     # 系统设置
│   └── LoginPage.vue        # 登录页
│
├── layouts/                 # 布局组件
│   └── MainLayout.vue       # 侧边栏 + 顶部栏 + 内容区
│
├── stores/                  # Pinia 状态管理
│   ├── app.ts               # Token、用户信息、登录状态
│   ├── tradeDate.ts         # 当前交易日
│   ├── job.ts               # 任务列表、10 秒轮询
│   └── selectionTemplate.ts # 选股模板
│
├── types/                   # TypeScript 类型定义
├── utils/                   # 工具函数
├── router/                  # Vue Router 配置
├── App.vue                  # 根组件
└── main.ts                  # 入口文件
```

### 页面与路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | → `/dashboard` | 重定向 |
| `/login` | LoginPage | 登录页 |
| `/dashboard` | DashboardPage | 系统概览、统计 |
| `/selection` | SelectionPage | 选股工作台 |
| `/stocks/:symbol` | StockDetailPage | 个股详情 |
| `/boards` | BoardListPage | 板块列表 |
| `/boards/:boardCode` | BoardDetailPage | 板块详情 |
| `/jobs` | JobListPage | ETL 任务管理 |
| `/jobs/:jobId` | JobDetailPage | 任务详情和日志 |
| `/coverage` | CoveragePage | 数据覆盖 |
| `/backfill` | BackfillPage | 历史回补 |
| `/watchlist` | WatchlistPage | 自选股 |
| `/settings` | SettingsPage | 系统设置 |

### 认证

- JWT Bearer token 存储在 `localStorage`
- Axios 拦截器自动在所有请求中注入 token
- 收到 401 响应时自动清除 token 并跳转到 `/login`

### 关键实现

1. **API 层**: `request.ts` 中统一封装 Axios 实例，处理错误
2. **任务轮询**: `JobStore` 每 10 秒轮询 `/api/v1/jobs?status=RUNNING`
3. **K 线图**: 使用 `lightweight-charts`（TradingView 开源库）
4. **虚拟滚动**: `vue-virtual-scroller` 用于大数据表格（>500 行）
5. **构建**: TypeScript 严格模式，`vue-tsc -b` 在 `vite build` 前执行

### 文档

- [前端架构设计](docs/A股股票信息缓存系统前端架构设计文档.md)
- [API 接口设计](docs/A股股票信息缓存系统前后端API接口设计文档.md)