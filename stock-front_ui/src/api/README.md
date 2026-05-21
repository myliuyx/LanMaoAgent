# API 层文档

> 本目录包含所有 API 接口的封装，统一通过 Axios 实例调用。

---

## 文件索引

| 文件 | 用途 |
|------|------|
| `request.ts` | Axios 实例封装（拦截器、错误处理、baseURL） |
| `auth.ts` | 认证相关接口 |
| `dashboard.ts` | Dashboard / 首页接口 |
| `selection.ts` | 选股相关接口 |
| `stock.ts` | 个股详情相关接口 |
| `board.ts` | 板块相关接口 |
| `job.ts` | 任务管理相关接口 |
| `coverage.ts` | 数据覆盖相关接口 |
| `backfill.ts` | 补历史相关接口 |

---

## request.ts - Axios 封装核心

### 导出内容
- `request: AxiosInstance` — 可复用的 Axios 实例

### 配置
```typescript
baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1'
timeout: 30000
```

### 请求拦截器
- 自动在 Header 中注入 `Authorization: Bearer <token>`（从 localStorage 读取）

### 响应拦截器
- `code === 0` → 返回 `response.data`（业务数据）
- `code !== 0` → ElMessage.error 提示 + Promise.reject
- HTTP 401 → 跳转登录页
- HTTP 403 → ElMessage.error 权限不足
- HTTP 500+ → ElMessage.error 服务器错误

---

## auth.ts - 认证接口

### 方法

#### `authApi.login(username: string, password: string)`
- **POST** `/auth/login`
- **返回**：`ApiResponse<LoginResponse>`
  ```typescript
  {
    token: string           // JWT token
    expires_in: number      // 过期时间（秒）
    user: { id, username, role }
  }
  ```

#### `authApi.verify()`
- **GET** `/auth/verify`
- **返回**：`ApiResponse<{ valid: boolean; user: {...} }>`

---

## dashboard.ts - Dashboard / 首页接口

### 类型

```typescript
interface DashboardSummary {
  latest_trade_date: string
  is_trade_day: boolean
  stock_count: number
  daily_record_count: number
  finance_record_count: number
  factor_record_count: number
  today_job_success_count: number
  today_job_failed_count: number
  selection_count: number
}

interface CoverageSummary {
  stocks_with_full_daily: number
  stocks_with_full_finance: number
  stocks_need_backfill: number
  total_stocks: number
}
```

### 方法

#### `dashboardApi.getSummary()`
- **GET** `/dashboard/summary`
- **返回**：`ApiResponse<DashboardSummary>`

#### `dashboardApi.getJobs(limit?: number)`
- **GET** `/dashboard/jobs`
- **返回**：`ApiResponse<JobItem[]>`

#### `dashboardApi.getCoverage()`
- **GET** `/dashboard/coverage`
- **返回**：`ApiResponse<CoverageSummary>`

---

## selection.ts - 选股接口

### 方法

#### `selectionApi.getDates(params?: { start_date?: string; end_date?: string; limit?: number })`
- **GET** `/selection/dates`
- **返回**：`ApiResponse<string[]>`（日期字符串数组）
- **说明**：`limit` 默认 100，最大 500

#### `selectionApi.query(data: SelectionQueryRequest)`
- **POST** `/selection/query`
- **请求体**：
  ```typescript
  {
    trade_date: string              // 必填，查询的交易日
    filters?: SelectionFilters      // 筛选条件
    sort_by?: string                // 排序字段
    sort_order?: 'asc' | 'desc'    // 排序方向
    page?: number                   // 页码
    page_size?: number              // 每页大小，默认 50
  }
  ```
- **返回**：`ApiResponse<PageResponse<SelectionItem>>`

#### `selectionApi.export(data: SelectionQueryRequest)`
- **POST** `/selection/export`
- **请求体**：同 `query`，但默认导出全部
- **返回**：Blob（CSV 文件流）

---

## stock.ts - 个股详情接口

### 方法

#### `stockApi.getProfile(symbol: string)`
- **GET** `/stocks/{symbol}/profile`
- **返回**：`ApiResponse<StockProfile>`

#### `stockApi.getDaily(symbol: string, params?: StockDailyQuery)`
- **GET** `/stocks/{symbol}/daily`
- **Query 参数**：`start_date?`、`end_date?`、`limit?`（默认 120）、`adjust?`（none/forward/backward）
- **返回**：`ApiResponse<StockDaily[]>`

#### `stockApi.getFactors(symbol: string, params?: { trade_date?: string; limit?: number })`
- **GET** `/stocks/{symbol}/factors`
- **Query 参数**：`trade_date?`、`limit?`（默认 60，返回最近 N 个交易日）
- **返回**：`ApiResponse<StockFactor[]>`

#### `stockApi.getFinance(symbol: string, limit?: number)`
- **GET** `/stocks/{symbol}/finance`
- **Query 参数**：`limit?`（默认 8，最大 40）
- **返回**：`ApiResponse<FinancialIndicator[]>`

#### `stockApi.getBoards(symbol: string)`
- **GET** `/stocks/{symbol}/boards`
- **返回**：`ApiResponse<StockBoard[]>`

#### `stockApi.getCoverage(symbol: string)`
- **GET** `/stocks/{symbol}/coverage`
- **返回**：`ApiResponse<DataCoverage[]>`

---

## board.ts - 板块接口

### 方法

#### `boardApi.getList(params?: { board_type?: string; keyword?: string; page?: number; page_size?: number })`
- **GET** `/boards`
- **返回**：`ApiResponse<PageResponse<BoardItem>>`

#### `boardApi.getDetail(boardCode: string)`
- **GET** `/boards/{boardCode}`
- **返回**：`ApiResponse<BoardDetail>`

#### `boardApi.getMembers(boardCode: string, params?: { trade_date?: string; page?: number; page_size?: number; sort_by?: string; sort_order?: 'asc' | 'desc' })`
- **GET** `/boards/{boardCode}/members`
- **返回**：`ApiResponse<PageResponse<BoardMember>>`

---

## job.ts - 任务管理接口

### 方法

#### `jobApi.getList(params?: JobQuery)`
- **GET** `/jobs`
- **Query 参数**：`job_name?`、`status?`、`biz_date?`、`page?`、`page_size?`
- **返回**：`ApiResponse<PageResponse<JobItem>>`

#### `jobApi.getDetail(jobId: number)`
- **GET** `/jobs/{jobId}`
- **返回**：`ApiResponse<JobItem>`

#### `jobApi.getLogs(jobId: number, params?: { offset?: number; limit?: number })`
- **GET** `/jobs/{jobId}/logs`
- **返回**：`ApiResponse<{ logs: string[]; total: number; offset: number; limit: number }>`

#### `jobApi.run(data: RunJobRequest)`
- **POST** `/jobs/run`
- **请求体**：`{ job_name, biz_date?, force?, params? }`
- **返回**：`ApiResponse<{ task_id, job_name, status, queue_position? }>`

#### `jobApi.cancel(jobId: number)`
- **POST** `/jobs/{jobId}/cancel`
- **返回**：`ApiResponse<null>`

---

## coverage.ts - 数据覆盖接口

### 方法

#### `coverageApi.getList(params?: { symbol?: string; data_type?: string; is_full_history?: boolean; page?: number; page_size?: number })`
- **GET** `/coverage`
- **返回**：`ApiResponse<PageResponse<DataCoverage>>`

#### `coverageApi.getDetail(symbol: string)`
- **GET** `/coverage/{symbol}`
- **返回**：`ApiResponse<{ symbol, name, coverages: DataCoverage[] }>`

---

## backfill.ts - 补历史接口

### 类型

```typescript
interface BackfillRunRequest {
  symbol: string
  data_type: 'DAILY' | 'FINANCE' | 'ADJUST_FACTOR'
  start_date?: string
  end_date?: string
  force?: boolean
}

interface BackfillStatus {
  task_id: number
  job_name: string
  status: string
  progress: number     // 0-100
  message: string
}
```

### 方法

#### `backfillApi.run(data: BackfillRunRequest)`
- **POST** `/backfill/run`
- **返回**：`ApiResponse<{ task_id, job_name, status }>`

#### `backfillApi.getStatus(taskId: number)`
- **GET** `/backfill/status/{taskId}`
- **返回**：`ApiResponse<BackfillStatus>`
