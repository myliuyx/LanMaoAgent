# Pages（路由页面组件）文档

> 本目录包含所有路由页面组件，每个文件对应一个路由。
> 所有页面都被 `MainLayout.vue` 包裹，在主布局的 `<slot />` 中渲染。

---

## 文件索引

| 文件 | 路由 | 说明 |
|------|------|------|
| `DashboardPage.vue` | `/dashboard` | 首页控制台 |
| `LoginPage.vue` | `/login` | 登录页 |
| `SelectionPage.vue` | `/selection` | 选股工作台 |
| `StockDetailPage.vue` | `/stocks/:symbol` | 个股详情 |
| `BoardListPage.vue` | `/boards` | 板块列表 |
| `BoardDetailPage.vue` | `/boards/:boardCode` | 板块详情 |
| `JobListPage.vue` | `/jobs` | 任务管理 |
| `JobDetailPage.vue` | `/jobs/:jobId` | 任务详情 |
| `CoveragePage.vue` | `/coverage` | 数据覆盖 |
| `BackfillPage.vue` | `/backfill` | 补历史 |
| `SettingsPage.vue` | `/settings` | 系统设置 |
| `NotFoundPage.vue` | `/*` | 404 页面 |

---

## DashboardPage.vue - 首页控制台

### 路由参数
无

### 核心功能
1. **数据总览卡片**（4 个统计卡片）：股票总数、日线记录数、财务记录数、因子记录数
2. **今日状态卡片**（4 个统计卡片）：最新交易日、今日成功/失败任务数、选股宽表记录数
3. **运行中任务列表**：展示当前 `runningJobs`，10 秒轮询更新

### 依赖 Store
- `useJobStore` — 调用 `startPolling()` / `stopPolling()`

### 依赖 API
- `dashboardApi.getSummary()` — 获取首页摘要
- `jobStore.runningJobs` — 运行中任务列表

### 页面布局
```
DashboardPage
├── 4个 el-row（el-col + el-card + el-statistic）
└── el-card（运行中任务 el-table）
```

---

## LoginPage.vue - 登录页

### 路由参数
无

### 核心功能
1. 用户名 + 密码表单
2. 调用 `authApi.login()` 获取 token
3. 存入 `useAppStore`
4. 成功后跳转 `/dashboard`

### 依赖 Store
- `useAppStore` — 调用 `setToken()` / `setUserInfo()`

### 依赖 API
- `authApi.login(username, password)`

### 布局
- 全屏居中布局
- 渐变背景
- 白色登录框

---

## SelectionPage.vue - 选股工作台

### 路由参数
无

### 核心功能
1. **交易日选择器**：下拉选择，默认选最新交易日
2. **筛选条件**：非ST、换手率、ROE、趋势评分等
3. **选股结果表格**：分页展示，点击行跳转到个股详情
4. **分页**：标准 Element Plus 分页

### 依赖 API
- `selectionApi.getDates()` — 获取可选交易日列表
- `selectionApi.query()` — 查询选股结果

### 表格列
`symbol`、`name`、`exchange`、`industry_l1`、`close`、`change_pct`、`turnover_rate`、`roe`、`trend_score`、`is_new_high_60d`、`is_st`

### 交互
- 点击行 → `router.push(/stocks/${row.symbol})`

---

## StockDetailPage.vue - 个股详情

### 路由参数
- `symbol` — 股票代码（格式如 `600519.SH`）

### 核心功能
1. **基本信息**：ElDescriptions 展示股票资料
2. **K 线图区域**：预留位置，待集成 `lightweight-charts`
3. **技术因子表格**：展示 MA、RSI、MACD、ATR 等
4. **财务指标表格**：展示 EPS、BPS、ROE、毛利率等
5. **所属板块**：ElTag 展示板块列表

### 依赖 API（全部使用 `Promise.all` 并行加载）
- `stockApi.getProfile(symbol)` — 股票资料
- `stockApi.getDaily(symbol, params)` — 日线行情
- `stockApi.getFactors(symbol, params)` — 技术因子
- `stockApi.getFinance(symbol)` — 财务指标
- `stockApi.getBoards(symbol)` — 所属板块

### 待完成
- `KLineChart.vue` 组件集成（使用 `lightweight-charts`）
- `VolumeChart.vue` 组件集成（配合 K 线图显示成交量）

---

## BoardListPage.vue - 板块列表

### 路由参数
无

### 核心功能
1. **搜索框**：按板块名称关键词搜索
2. **板块表格**：展示板块代码、名称、类型、成分股数

### 依赖 API
- `boardApi.getList(params)` — 获取板块列表

### 交互
- 点击行 → `router.push(/boards/${row.board_code})`

---

## BoardDetailPage.vue - 板块详情

### 路由参数
- `boardCode` — 板块代码

### 核心功能
1. **板块信息**：板块名称、类型、成分股数
2. **成分股表格**：展示成分股涨跌幅、换手率、趋势评分

### 依赖 API
- `boardApi.getDetail(boardCode)` — 板块详情
- `boardApi.getMembers(boardCode, params)` — 成分股列表

### 交互
- 点击行 → `router.push(/stocks/${row.symbol})`

---

## JobListPage.vue - 任务管理

### 路由参数
无

### 核心功能
1. **任务表格**：展示任务名称、状态、耗时、写入条数、错误信息
2. **状态 Tag**：根据 `JOB_STATUS_MAP` 显示状态颜色
3. **分页**：标准分页

### 依赖 API
- `jobApi.getList(params)` — 获取任务列表

### 交互
- 点击行 → `router.push(/jobs/${row.id})`

---

## JobDetailPage.vue - 任务详情

### 路由参数
- `jobId` — 任务 ID（数字）

### 核心功能
1. **任务详情 ElDescriptions**：展示所有任务字段
2. **执行日志 ElScrollbar**：展示任务运行日志，支持滚动

### 依赖 API
- `jobApi.getDetail(jobId)` — 任务详情
- `jobApi.getLogs(jobId)` — 任务日志

---

## CoveragePage.vue - 数据覆盖

### 路由参数
无

### 核心功能
1. **搜索条件**：股票代码、数据类型筛选
2. **覆盖表格**：展示数据覆盖范围、是否完整历史

### 依赖 API
- `coverageApi.getList(params)` — 获取覆盖列表

---

## BackfillPage.vue - 补历史

### 路由参数
无

### 核心功能
1. **补数表单**：股票代码、数据类型、起始日期、结束日期、是否强制覆盖
2. **提交**：调用 `backfillApi.run()` 提交补数任务

### 依赖 API
- `backfillApi.run(data)` — 触发补历史任务

---

## SettingsPage.vue - 系统设置

### 路由参数
无

### 核心功能
1. **系统信息**：环境、版本、数据库状态、调度器状态
- 目前为静态展示，待接入真实接口

---

## NotFoundPage.vue - 404 页面

### 路由参数
无

### 核心功能
1. **404 大字展示**
2. **返回首页按钮** → `router.push('/dashboard')`
