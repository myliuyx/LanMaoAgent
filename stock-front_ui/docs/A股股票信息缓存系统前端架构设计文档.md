# A股股票信息缓存系统前端架构设计文档

> 版本：v2.0（基于 v1.0 review 建议更新）
> 更新日期：2026-04-18

---

## 1. 前端系统目标

前端系统核心目标是给本地数据平台提供可视化操作入口，是「数据平台控制台+选股分析台+运维监控台」三合一的工作台，主要服务场景：

- 查看每日同步状态
- 浏览全市场选股结果
- 查询个股历史行情与财务
- 按条件筛选股票
- 查看板块成分和板块表现
- 触发初始化、补历史、重跑任务
- 查看数据覆盖范围和任务日志

---

## 2. 前端定位与边界

### 2.1 第一版应该做什么

| 页面类型 | 核心功能 |
|----------|----------|
| 系统控制台 | 任务状态、当日同步情况、错误日志摘要、数据覆盖情况 |
| 选股工作台 | 每日选股宽表查询、条件筛选、排序和导出、保存筛选条件 |
| 个股详情页 | 基本信息、日线行情、技术因子、财务指标、板块归属、数据覆盖范围 |
| 板块分析页 | 板块列表、板块成分股、板块强弱排序 |
| 任务管理页 | 查看任务运行记录、查看失败任务、手工触发任务、查看检查点和补数状态 |

### 2.2 第一版不建议做什么

避免架构失控，第一版暂时不开发：

- 实时分时图大屏、高频盘口刷新
- 富交互画线分析器、专业交易终端级复杂图表系统
- 用户权限极复杂的多租户后台

> 原因：后端当前是离线分析底座，不是高频实时行情引擎，前端优先围绕**查询、分析、筛选、运维**设计。

### 2.3 明确不做的事

以下内容**第一版明确不实现**，仅作架构预留：

- WebSocket 实时推送（任务状态通过轮询实现）
- 多用户权限系统（第一版单用户，可跳过登录或仅简单 token 验证）
- 移动端适配（专注桌面端）

---

## 3. 前端总体架构思路

整体采用「BFF/API层 + Web管理前端 + 图表组件层」三层架构：

```
前端页面层（Vue 3 + TypeScript）
    ↓
前端状态与组件层（Pinia + Element Plus）
    ↓
后端API层（FastAPI）
    ↓
数据库与任务系统（PostgreSQL + ETL任务）
```

---

## 4. 技术选型

| 层级 | 推荐方案 | 说明 |
|------|----------|------|
| 前端框架 | Vue 3 + TypeScript | 后台管理+数据分析台场景上手快 |
| UI组件库 | Element Plus | 成熟的后台组件库，开箱即用 |
| 状态管理 | Pinia | Vue 3 官方推荐状态管理方案 |
| 路由 | Vue Router | 官方路由方案 |
| 请求库 | Axios | 成熟的 HTTP 请求库 |
| 图表库 | ECharts + lightweight-charts | ECharts 处理常规图表；**K线图用 lightweight-charts（TradingView 开源库）**，支持缩放、拖拽、标注 |
| 表格方案 | Element Plus Table + 虚拟滚动 | 大数据量用 `vue-virtual-scroller` 虚拟滚动 |
| 构建工具 | Vite | 开发速度快，构建效率高 |
| 权限控制 | 简单 token 验证（第一版） | 避免完全无验证，但不做复杂 RBAC |

### 4.1 图表库选型说明

| 图表类型 | 推荐方案 | 原因 |
|----------|----------|------|
| 常规图表（折线、柱状、饼图） | ECharts | 成熟稳定，配置灵活 |
| K线图 / 个股走势 | **lightweight-charts** | TradingView 开源，专业金融图表，支持缩放拖拽，性能优秀 |
| 成交量柱状图 | ECharts（与 K线图组合） | 配合 lightweight-charts 使用 |

### 4.2 lightweight-charts 引入方式

```bash
npm install lightweight-charts
```

```typescript
import { createChart } from 'lightweight-charts'

// 个股日线 K线图示例
const chart = createChart(containerRef, { width: 800, height: 400 })
const candleSeries = chart.addCandlestickSeries()
candleSeries.setData(ohlcData)
```

---

## 5. 登录与权限设计

### 5.1 第一版方案：简化 token 验证

| 项目 | 方案 |
|------|------|
| 登录方式 | 简单 token 放在请求头或 localStorage，不做复杂登录页 |
| token 验证 | 后端提供一个 `/api/v1/auth/verify` 接口验证 token 有效性 |
| 权限控制 | 第一版不区分角色，所有登录用户同等权限 |

### 5.2 后续扩展方向

- 引入正式 JWT 登录流程
- 角色划分：管理员 / 分析用户 / 只读用户
- 权限控制范围：是否可触发任务、是否可导出数据、是否可补历史

---

## 6. 前端模块划分

按业务模块拆分，避免按页面样式拆分：

### 6.1 Dashboard 模块（首页/工作台入口）

- 核心功能：显示今日是否交易日、今日同步任务状态、最近任务失败告警、当前数据库记录规模、今日选股结果数量、数据覆盖范围摘要
- 主要组件：今日任务卡片、数据总览卡片、最近错误列表、数据同步趋势图、最近交易日摘要
- 依赖接口：`/api/v1/dashboard/summary`、`/api/v1/dashboard/jobs`、`/api/v1/dashboard/coverage`

### 6.2 选股工作台模块（核心业务模块）

- 核心功能：查询某个交易日的选股宽表、设置筛选条件、条件排序、分页浏览、导出结果、保存常用选股模板
- 支持筛选条件示例：非ST、收盘价大于MA20、60日新高、换手率>3%、ROE>10%、营收同比>20%、行业=半导体、市值区间筛选
- 页面结构：顶部交易日选择、左侧筛选器面板、右侧结果表格、顶部工具区（导出、保存条件、快速模板）
- 大数据量处理：结果超过 500 条时启用虚拟滚动
- 依赖接口：`/api/v1/selection/dates`、`/api/v1/selection/query`、`/api/v1/selection/export`、`/api/v1/selection/templates`

### 6.3 个股详情模块（第二核心模块）

- 核心功能：展示单只股票全景信息
- 页面分区：
  - 基本信息区：股票名称、代码、所属市场、行业、上市日期、当前状态
  - 行情信息区：最新日线摘要、K线图（lightweight-charts）、成交量柱状图（ECharts）、涨跌幅区间统计
  - 技术因子区：MA系列、RSI、MACD、ATR、趋势评分、新高新低状态
  - 财务信息区：ROE、营收同比、净利润同比、EPS、经营现金流
  - 板块归属区：所属行业、所属概念、所属指数成分
  - 数据覆盖区：日线覆盖到哪里、财务覆盖到哪里、是否已补全历史
- 依赖接口：`/api/v1/stocks/{symbol}/profile`、`/api/v1/stocks/{symbol}/daily`、`/api/v1/stocks/{symbol}/factors`、`/api/v1/stocks/{symbol}/finance`、`/api/v1/stocks/{symbol}/boards`、`/api/v1/stocks/{symbol}/coverage`

### 6.4 板块分析模块

- 核心功能：查看板块列表、板块成分股、板块内股票排序、板块热度与强弱
- 页面结构：左侧板块列表、右侧板块详情+成分股表格、顶部板块类型切换（行业/概念/指数）
- 依赖接口：`/api/v1/boards`、`/api/v1/boards/{board_code}`、`/api/v1/boards/{board_code}/members`

### 6.5 数据任务管理模块（运维中枢）

- 核心功能：查看任务执行列表、查看任务明细、查看错误信息、手动重跑任务、查看任务检查点
- 实时性策略：**短轮询**（每 10 秒请求一次 `/api/v1/jobs` 获取最新状态），第一版不做 WebSocket
- 页面结构：任务列表页、任务详情抽屉/弹窗、任务运行日志页
- 依赖接口：`/api/v1/jobs`、`/api/v1/jobs/{id}`、`/api/v1/jobs/{id}/logs`、`/api/v1/jobs/run`、`/api/v1/checkpoints`

### 6.6 数据覆盖与补数模块

- 核心功能：查询某只股票数据覆盖情况、查询哪些股票未补全历史、触发按股票补历史任务、查看补数进度
- 依赖接口：`/api/v1/coverage`、`/api/v1/coverage/{symbol}`、`/api/v1/backfill/run`、`/api/v1/backfill/status/{taskId}`

---

## 7. 任务状态实时更新机制

### 7.1 方案：短轮询

| 项目 | 说明 |
|------|------|
| 轮询间隔 | 10 秒（Dashboard 和任务列表页面） |
| 触发时机 | 页面可见时启动，用户离开页面时停止 |
| 接口 | GET `/api/v1/jobs`（带 `status=RUNNING` 过滤） |
| 后续扩展 | 可升级为 WebSocket，需要后端支持 |

### 7.2 任务完整状态枚举

| 状态 | 说明 |
|------|------|
| PENDING | 排队中，等待执行 |
| RUNNING | 执行中 |
| SUCCESS | 执行成功 |
| FAILED | 执行失败 |
| CANCELLED | 已取消 |

> 第一版前端仅展示 `RUNNING / SUCCESS / FAILED` 三种主要状态，`PENDING` 和 `CANCELLED` 作为后续扩展。

### 7.3 前端轮询实现示例

```typescript
// JobListPage.vue
import { ref, onMounted, onUnmounted } from 'vue'

const jobs = ref([])
let pollTimer = null

const startPolling = () => {
  pollTimer = setInterval(async () => {
    jobs.value = await fetchJobs({ status: 'RUNNING' })
  }, 10000)
}

const stopPolling = () => {
  if (pollTimer) clearInterval(pollTimer)
}

onMounted(startPolling)
onUnmounted(stopPolling)
```

---

## 8. 前端页面结构

```
首页 Dashboard
├── 今日同步状态
├── 数据总览
├── 失败任务
└── 覆盖范围摘要

选股工作台
├── 条件筛选面板
├── 每日选股结果表（虚拟滚动）
├── 导出功能
└── 筛选模板

个股详情页
├── 基本信息
├── K线与成交量（lightweight-charts + ECharts）
├── 技术因子
├── 财务指标
├── 板块归属
└── 数据覆盖情况

板块分析页
├── 板块列表
├── 板块详情
└── 成分股列表

任务管理页
├── 任务列表（支持轮询实时状态）
├── 任务详情
├── 错误信息
└── 手工触发

数据覆盖页
├── 覆盖范围列表
├── 缺口分析
└── 补历史操作
```

---

## 9. 前端组件分层设计

三层组件分离：

### 9.1 页面级组件（对应路由页面）

- 示例：`DashboardPage`、`SelectionPage`、`StockDetailPage`、`BoardAnalysisPage`、`JobManagePage`
- 职责：页面结构组织、调用API、控制整体状态

### 9.2 业务组件（可复用业务区块）

- 示例：`JobStatusCard`、`SelectionFilterPanel`、`StockBasicInfoCard`、`StockFactorTable`、`FinanceSummaryCard`、`BoardMemberTable`、`CoverageStatusPanel`
- 职责：单个业务块展示与交互、不处理全局路由逻辑

### 9.3 通用组件（纯UI或工具性组件）

- 示例：`BaseTable`（封装虚拟滚动）、`BaseChart`、`BaseDatePicker`、`BaseStatCard`、`BaseDrawer`、`BaseTag`
- 职责：提高一致性、减少重复开发

### 9.4 大数据量表格封装建议

```typescript
// components/base/VirtualTable.vue
// 基于 vue-virtual-scroller 封装，支持大数据量
<template>
  <RecycleScroller :items="data" :item-size="40" key-field="id">
    <template #default="{ item }">
      <slot :item="item" />
    </template>
  </RecycleScroller>
</template>
```

---

## 10. 状态管理设计

使用 Pinia 管理前端状态：

### 10.1 全局状态（Store 管理）

- `useAppStore` - 当前用户信息、token、主题配置
- `useTradeDateStore` - 当前系统交易日
- `useJobStore` - 全局任务状态（用于 Dashboard 和 JobManage 共享）
- `useSelectionTemplateStore` - 筛选模板缓存

### 10.2 页面局部状态（组件内部管理）

- 单个页面临时表单
- 局部查询结果
- 临时弹窗数据

### 10.3 JobStore 设计示例

```typescript
// stores/job.ts
export const useJobStore = defineStore('job', () => {
  const runningJobs = ref([])
  const latestJobs = ref([])

  const fetchRunningJobs = async () => {
    const res = await axios.get('/api/v1/jobs', { params: { status: 'RUNNING' } })
    runningJobs.value = res.data.data.list
  }

  // 供 Dashboard 和 JobManagePage 共享
  return { runningJobs, latestJobs, fetchRunningJobs }
})
```

---

## 11. API对接层设计

统一封装 API 层：

### 11.1 目录结构

```
src/api/
├── dashboard.ts
├── selection.ts
├── stock.ts
├── board.ts
├── job.ts
├── coverage.ts
├── backfill.ts
└── auth.ts
```

### 11.2 统一处理内容

- baseURL 设置
- token 自动注入
- 超时配置（默认 30 秒）
- 错误统一提示
- 响应结构解包（code === 0 为成功）

### 11.3 请求封装示例

```typescript
// utils/request.ts
import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000
})

request.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

request.interceptors.response.use(
  response => {
    const { code, message, data } = response.data
    if (code !== 0) {
      ElMessage.error(message || '请求失败')
      return Promise.reject(response.data)
    }
    return data
  },
  error => {
    ElMessage.error(error.message || '网络错误')
    return Promise.reject(error)
  }
)

export default request
```

---

## 12. 图表设计建议

### 12.1 推荐图表场景

| 图表类型 | 工具 | 场景 |
|----------|------|------|
| K线图 | lightweight-charts | 个股日线走势 |
| 成交量柱状图 | ECharts | 配合 K线图展示成交量 |
| 收盘价折线图 | ECharts | 均线趋势 |
| 板块涨跌分布图 | ECharts | 行业/板块涨跌对比 |
| 任务执行趋势图 | ECharts | 同步数量趋势 |
| 数据同步数量趋势图 | ECharts | 历史同步规模 |

### 12.2 第一版不建议开发

- 复杂自定义 K线交互编辑器
- 画线工具
- 多窗口叠加比较系统

---

## 13. 权限与用户设计

### 13.1 第一版（单用户简化方案）

```typescript
// stores/app.ts
export const useAppStore = defineStore('app', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    isLoggedIn: !!localStorage.getItem('token')
  }),
  actions: {
    setToken(token: string) {
      this.token = token
      this.isLoggedIn = true
      localStorage.setItem('token', token)
    },
    logout() {
      this.token = ''
      this.isLoggedIn = false
      localStorage.removeItem('token')
    }
  }
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const appStore = useAppStore()
  if (!appStore.isLoggedIn && to.path !== '/login') {
    next('/login')
  } else {
    next()
  }
})
```

### 13.2 后续扩展（多人使用）

- 角色划分：管理员、分析用户、只读用户
- 权限控制范围：是否可触发任务、是否可导出数据、是否可补历史、是否可查看系统配置

---

## 14. 前端项目目录结构

```
frontend/
├── public/
├── src/
│   ├── api/                 # API层统一封装
│   │   ├── dashboard.ts
│   │   ├── selection.ts
│   │   ├── stock.ts
│   │   ├── board.ts
│   │   ├── job.ts
│   │   ├── coverage.ts
│   │   ├── backfill.ts
│   │   └── auth.ts
│   ├── assets/              # 静态资源
│   ├── components/          # 组件层
│   │   ├── base/            # 通用基础组件
│   │   │   ├── VirtualTable.vue    # 虚拟滚动表格
│   │   │   ├── BaseChart.vue
│   │   │   ├── BaseDatePicker.vue
│   │   │   ├── BaseStatCard.vue
│   │   │   └── BaseDrawer.vue
│   │   ├── dashboard/       # Dashboard模块业务组件
│   │   ├── selection/       # 选股模块业务组件
│   │   ├── stock/           # 个股模块业务组件
│   │   ├── board/           # 板块模块业务组件
│   │   └── job/             # 任务模块业务组件
│   ├── layouts/             # 布局组件
│   │   └── MainLayout.vue
│   ├── pages/               # 页面级组件
│   │   ├── DashboardPage.vue
│   │   ├── SelectionPage.vue
│   │   ├── StockDetailPage.vue
│   │   ├── BoardAnalysisPage.vue
│   │   ├── JobManagePage.vue
│   │   ├── CoveragePage.vue
│   │   └── LoginPage.vue
│   ├── router/              # 路由配置
│   │   └── index.ts
│   ├── stores/              # 状态管理
│   │   ├── app.ts
│   │   ├── tradeDate.ts
│   │   ├── job.ts
│   │   └── selectionTemplate.ts
│   ├── types/               # TypeScript类型定义
│   │   ├── common.ts
│   │   ├── stock.ts
│   │   ├── selection.ts
│   │   └── job.ts
│   ├── utils/               # 工具函数
│   │   ├── request.ts       # 统一请求封装
│   │   ├── format.ts        # 格式化工具
│   │   └── constants.ts     # 常量定义
│   ├── App.vue
│   └── main.ts
├── package.json
├── vite.config.ts
└── README.md
```

---

## 15. 页面交互原则

### 15.1 结果优先

页面重点不是装饰，而是快速查询、快速筛选、快速定位异常。

### 15.2 表格优先

表格是第一生产力，支持列排序、筛选、固定列、导出 CSV/Excel、跳转个股详情。

### 15.3 图表做辅助，不喧宾夺主

图表主要帮助理解趋势，不要过度设计。

### 15.4 所有关键操作有反馈

手工触发任务、导出、补历史等操作后要有明确提示和状态显示。

### 15.5 虚拟滚动保障大数据量性能

选股结果表、板块成分股表等超过 500 条时启用虚拟滚动，避免页面卡顿。

---

## 16. 前端开发阶段建议

### 16.1 第一阶段：最小工作台

- 完成：登录验证（简化版）、主布局、Dashboard、任务管理页、选股工作台基础版
- 目标：能看数据、能查选股、能看任务状态

### 16.2 第二阶段：分析能力增强

- 完成：个股详情页（含 K线图）、板块分析页、图表能力、导出能力、筛选模板
- 目标：能深度分析股票、能按板块看机会

### 16.3 第三阶段：运维与补数增强

- 完成：数据覆盖页、补历史入口、任务重跑入口、异常提示中心
- 目标：让前端成为真正的控制台

---

## 17. 架构优势总结

- **技术栈成熟**：Vue 3 + TypeScript + Vite 开发效率高
- **K线图专业**：lightweight-charts 补足 ECharts 在金融图表上的不足
- **性能保障**：虚拟滚动解决大数据量表格性能问题
- **实时性可行**：轮询方案满足第一版需求，后续可升级 WebSocket
- **权限简化**：简单 token 方案防误操作，不过度设计
- **与后台天然匹配**：API 设计面向业务，不面向数据库
