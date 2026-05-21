# Types（TypeScript 类型定义）文档

> 本目录包含项目中使用的所有 TypeScript 类型定义。
> 遵循前后端字段命名一致原则（snake_case）。

---

## 文件索引

| 文件 | 类型 |
|------|------|
| `common.ts` | 通用类型（ApiResponse、PageResponse 等） |
| `job.ts` | 任务相关类型和状态枚举 |
| `stock.ts` | 股票相关类型（资料、日线、因子、财务等） |
| `selection.ts` | 选股相关类型（筛选条件、查询请求、结果项） |
| `board.ts` | 板块相关类型（板块项、成分股） |

---

## common.ts - 通用类型

### ApiResponse<T>
```typescript
interface ApiResponse<T> {
  code: number    // 0 = 成功，非 0 = 失败
  message: string // 错误信息
  data: T         // 业务数据
}
```

### PageResponse<T>
```typescript
interface PageResponse<T> {
  list: T[]        // 数据列表
  page: number     // 当前页码
  page_size: number // 每页大小
  total: number    // 总记录数
}
```

### LoginResponse
```typescript
interface LoginResponse {
  token: string
  expires_in: number
  user: { id: number; username: string; role: string }
}
```

---

## job.ts - 任务相关类型

### JobStatus（任务状态枚举）
```typescript
type JobStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'CANCELLED'
```

| 状态 | 说明 | 前端 Tag 类型 |
|------|------|---------------|
| PENDING | 排队中 | info |
| RUNNING | 运行中 | warning |
| SUCCESS | 成功 | success |
| FAILED | 失败 | danger |
| CANCELLED | 已取消 | info |

### JobItem
```typescript
interface JobItem {
  id: number
  job_name: string
  biz_date: string | null         // 业务日期
  status: JobStatus
  start_time: string               // ISO 8601
  end_time: string | null          // ISO 8601
  duration_ms: number | null       // 耗时（毫秒）
  rows_raw: number | null          // 原始记录数
  rows_written: number | null      // 写入记录数
  error_message: string | null    // 错误信息
}
```

### JobQuery
```typescript
interface JobQuery {
  job_name?: string
  status?: JobStatus
  biz_date?: string
  page?: number
  page_size?: number
}
```

### RunJobRequest
```typescript
interface RunJobRequest {
  job_name: string
  biz_date?: string
  force?: boolean          // 是否强制重跑（跳过检查点）
  params?: Record<string, unknown>
}
```

---

## stock.ts - 股票相关类型

### StockProfile（股票基础资料）
```typescript
interface StockProfile {
  symbol: string
  name: string
  exchange: string          // SH / SZ / BJ
  ticker: string            // 纯数字代码
  security_type: string | null
  list_board: string | null // 上市板块（主板/科创板/创业板）
  list_date: string | null  // 上市日期
  delist_date: string | null // 退市日期
  status: 'LISTED' | 'DELISTED' | 'SUSPENDED'
  is_st: boolean             // 是否 ST（根据名称含 ST 或数据库字段判断）
  industry_l1: string | null
  industry_l2: string | null
  area: string | null
}
```

### StockDaily（日线行情）
```typescript
interface StockDaily {
  trade_date: string
  open: number              // 开盘价（元）
  high: number              // 最高价（元）
  low: number               // 最低价（元）
  close: number             // 收盘价（元）
  pre_close: number         // 前收价（元）
  change_amount: number     // 涨跌额（元）
  change_pct: number        // 涨跌幅（%）
  volume: number            // 成交量（股）
  amount: number            // 成交额（元）
  turnover_rate: number     // 换手率（%）
  amplitude: number         // 振幅（%）
  market_value: number      // 总市值（元）
  circ_market_value: number // 流通市值（元）
}
```

### StockDailyQuery（日线查询参数）
```typescript
interface StockDailyQuery {
  start_date?: string       // YYYY-MM-DD
  end_date?: string         // YYYY-MM-DD
  limit?: number            // 默认 120，最大 730
  adjust?: 'none' | 'forward' | 'backward'  // 复权类型，默认 forward
}
```

### StockFactor（技术因子）
```typescript
interface StockFactor {
  trade_date: string
  ma5: number | null        // 5 日均线（元）
  ma10: number | null       // 10 日均线（元）
  ma20: number | null       // 20 日均线（元）
  ma60: number | null       // 60 日均线（元）
  rsi_6: number | null      // 6 日 RSI
  rsi_14: number | null     // 14 日 RSI
  atr_14: number | null     // 14 日 ATR
  macd_dif: number | null   // MACD 快线（DIF）
  macd_dea: number | null   // MACD 慢线（DEA）
  macd_hist: number | null  // MACD 柱状图（HIST = DIF - DEA）
  is_new_high_60d: boolean   // 是否 60 日新高
  is_break_ma20: boolean    // 是否站上 MA20
  trend_score: number | null // 趋势评分（0-100）
}
```

### FinancialIndicator（财务指标）
```typescript
interface FinancialIndicator {
  report_period: string     // 报告期（YYYY-MM-DD）
  report_type: 'Q1' | 'H1' | 'Q3' | 'FY'
  announce_date: string     // 公告日期
  eps: number | null       // 每股收益（元）
  bps: number | null       // 每股净资产（元）
  roe: number | null       // ROE（%）
  gross_margin: number | null // 毛利率（%）
  net_margin: number | null  // 净利率（%）
  revenue: number | null    // 营业收入（元）
  net_profit: number | null // 净利润（元）
  revenue_yoy: number | null // 营收同比（%）
  net_profit_yoy: number | null // 净利润同比（%）
  ocf: number | null        // 经营现金流（元）
}
```

### StockBoard（所属板块）
```typescript
interface StockBoard {
  board_code: string
  board_name: string
  board_type: 'INDUSTRY' | 'CONCEPT' | 'INDEX' | 'AREA'
  update_date: string
}
```

### DataCoverage（数据覆盖）
```typescript
interface DataCoverage {
  symbol: string
  data_type: 'DAILY' | 'FINANCE' | 'ADJUST_FACTOR'
  start_date: string | null
  end_date: string | null
  is_full_history: boolean
  last_sync_at: string | null
}
```

---

## selection.ts - 选股相关类型

### SelectionFilters（筛选条件）
```typescript
interface SelectionFilters {
  keyword?: string           // 股票代码或名称模糊搜索
  exchange?: string          // SH / SZ / BJ
  industry_l1?: string       // 一级行业
  is_st?: boolean            // 是否 ST
  market_value_min?: number  // 最小总市值（元）
  market_value_max?: number  // 最大总市值（元）
  turnover_rate_min?: number // 最小换手率（%）
  turnover_rate_max?: number // 最大换手率（%）
  roe_min?: number           // 最小 ROE（%）
  roe_max?: number           // 最大 ROE（%）
  revenue_yoy_min?: number   // 最小营收同比（%）
  net_profit_yoy_min?: number // 最小净利润同比（%）
  is_new_high_60d?: boolean  // 是否 60 日新高
  is_break_ma20?: boolean    // 是否站上 MA20
  trend_score_min?: number   // 最小趋势评分
}
```

### SelectionQueryRequest（查询请求）
```typescript
interface SelectionQueryRequest {
  trade_date: string          // 必填
  filters?: SelectionFilters
  sort_by?: string           // 默认 'trend_score'
  sort_order?: 'asc' | 'desc' // 默认 'desc'
  page?: number              // 默认 1
  page_size?: number         // 默认 50
}
```

### SelectionItem（选股结果项）
```typescript
interface SelectionItem {
  symbol: string
  name: string
  exchange: string
  industry_l1: string | null
  close: number | null
  change_pct: number | null
  turnover_rate: number | null
  market_value: number | null
  roe: number | null
  revenue_yoy: number | null
  net_profit_yoy: number | null
  ma20: number | null
  ma60: number | null
  is_new_high_60d: boolean | null
  trend_score: number | null
  is_st: boolean
}
```

---

## board.ts - 板块相关类型

### BoardType（板块类型枚举）
```typescript
type BoardType = 'INDUSTRY' | 'CONCEPT' | 'INDEX' | 'AREA'
```

| 类型 | 说明 |
|------|------|
| INDUSTRY | 行业 |
| CONCEPT | 概念 |
| INDEX | 指数 |
| AREA | 地域 |

### BoardItem（板块项）
```typescript
interface BoardItem {
  board_code: string
  board_name: string
  board_type: BoardType
  member_count: number
  is_active: boolean
}
```

### BoardDetail（板块详情）
```typescript
interface BoardDetail {
  board_code: string
  board_name: string
  board_type: BoardType
  parent_board_code: string | null
  is_active: boolean
}
```

### BoardMember（成分股项）
```typescript
interface BoardMember {
  symbol: string
  name: string
  exchange: string
  close: number | null
  change_pct: number | null
  turnover_rate: number | null
  market_value: number | null
  trend_score: number | null
  industry_l1: string | null
}
```
