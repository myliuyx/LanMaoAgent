# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A-stock (A股) stock information caching system frontend — a Vue 3 + TypeScript admin dashboard + stock analysis console + operations monitoring dashboard. Serves as a visual control panel for a local data platform backed by a FastAPI backend.

**Tech stack**: Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router + Axios + ECharts + lightweight-charts

## Commands

```bash
# Install dependencies
npm install

# Start dev server (port 5173, proxies /api to http://192.168.3.18:8000)
npm run dev

# Build production bundle
npm run build

# Preview built output
npm run preview
```

Type checking is done via `vue-tsc` as part of `npm run build` (no separate test command exists).

## Architecture

### Entry and bootstrap
- `src/main.ts` — creates Vue app, registers Pinia, Router, ElementPlus (zh-CN locale)
- `src/App.vue` — wraps `MainLayout` + `RouterView`

### Routing (`src/router/index.ts`)
History mode, lazy-loaded route components. Auth guard checks `localStorage.getItem('token')`; redirects unauthenticated users to `/login`. Routes:

| Path | Component | Purpose |
|------|-----------|---------|
| `/` | → `/dashboard` | Redirect |
| `/login` | LoginPage | Login |
| `/dashboard` | DashboardPage | Console overview |
| `/selection` | SelectionPage | Stock screening workstation |
| `/watchlist` | WatchlistPage | Watchlist management |
| `/stocks/:symbol` | StockDetailPage | Individual stock detail |
| `/boards` | BoardListPage | Sector/plate list |
| `/boards/:boardCode` | BoardDetailPage | Sector detail |
| `/jobs` | JobListPage | Task management |
| `/jobs/:jobId` | JobDetailPage | Task detail |
| `/coverage` | CoveragePage | Data coverage |
| `/backfill` | BackfillPage | Historical data backfill |
| `/settings` | SettingsPage | System settings |
| `/*` | NotFoundPage | 404 |

### API layer (`src/api/`)
Unified Axios instance in `src/api/request.ts` with:
- Base URL: `/api/v1` (via `VITE_API_BASE_URL`)
- Bearer token injection from `localStorage`
- Business error code handling (`code !== 0` → reject with `isBusinessError`)
- HTTP error handling: 401 clears token and redirects to `/login`, 403/5xx/user-friendly messages

API modules by domain: `auth.ts`, `dashboard.ts`, `selection.ts`, `stock.ts`, `board.ts`, `job.ts`, `coverage.ts`, `backfill.ts`, `watchlist.ts`

### State management (`src/stores/`)
- `app.ts` — token, user info, login state
- `tradeDate.ts` — current trading day
- `job.ts` — task list, running jobs, polling (10s interval for RUNNING jobs)
- `selectionTemplate.ts` — stock screening template management

### Components (`src/components/`)
Flat subdirectory structure by module:
- **base/**: `BaseChart`, `BaseDatePicker`, `BaseDrawer`, `BaseEmpty`, `BaseStatCard`, `BaseTag`, `VirtualTable` (vue-virtual-scroller)
- **job/**: `JobLogViewer`
- **selection/**: `FilterPanel`, `ResultTable`
- **stock/**: `KLineChart` (lightweight-charts), `VolumeChart` (ECharts)

### Types (`src/types/`)
`common.ts`, `job.ts`, `stock.ts`, `selection.ts`, `board.ts`, `watchlist.ts`

### Layout
`src/layouts/MainLayout.vue` — sidebar + top bar + content area

### Charts
- K-line charts: `lightweight-charts` (in `KLineChart.vue`)
- Volume/regular charts: ECharts (in `VolumeChart.vue`, `BaseChart.vue`)

## Key patterns

1. **Auth**: Token stored in `localStorage`, injected as `Authorization: Bearer` header. 401 responses auto-redirect to `/login`.
2. **Task polling**: `JobStore` polls `/api/v1/jobs?status=RUNNING` every 10s when visible pages are mounted.
3. **Mock data**: Enable with `VITE_USE_MOCK=true` in `.env.development`. Mocks live in `mock/` directory.
4. **Virtual scrolling**: `vue-virtual-scroller` used for large tables (>500 rows) via `VirtualTable.vue`.
5. **Build**: TypeScript strict mode enabled. `vue-tsc -b` runs before `vite build`.

## Deployment

Docker multi-stage build: Node 20 builder → Nginx Alpine serving `dist/`. Nginx config at `nginx.conf`.

## Documentation Index

| 文档 | 说明 |
|------|------|
| [前后端API接口设计文档](../stock-front_ui/docs/A股股票信息缓存系统前后端API接口设计文档.md) | 前端视角 API 速查（含字段协议、TypeScript类型定义） |
| [前端架构设计文档](../stock-front_ui/docs/A股股票信息缓存系统前端架构设计文档.md) | 前端系统设计（技术栈、模块划分、状态管理） |
| [定时任务使用文档](../stock-fast-api/docs/定时任务使用文档.md) | ETL 任务配置管理 |
| [故障排查指南](../docs/TROUBLESHOOTING.md) | 常见问题与解决方案 |

> API 完整文档（权威来源）→ [`stock-fast-api/docs/REGISTRY.md`](../stock-fast-api/docs/REGISTRY.md)
