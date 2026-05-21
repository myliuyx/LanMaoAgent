# A股股票信息缓存系统前后端API接口设计文档

> 版本：v2.0（基于 v1.0 review 建议更新）
> 更新日期：2026-04-18

---

## 1. 文档目标

本份文档定义两部分核心内容：

1. 前端页面清单与路由设计
2. 前后端API清单与字段协议定义

**适用范围**：本地股票数据分析平台，对接PostgreSQL + FastAPI + Vue 3前端，面向离线同步后的日线、财务、因子、板块、任务管理等功能。
**设计定位**：可查询、可筛选、可分析、可运维的股票数据工作台，而非通用证券门户网站。

---

## 2. 前端页面清单总览

### 完整页面地图

| 页面模块 | 页面名称 | 路由 | 主要作用 |
|----------|----------|------|----------|
| 首页 | Dashboard首页 | /dashboard | 查看系统摘要、任务状态、数据规模 |
| 选股 | 选股工作台 | /selection | 条件筛选、排序、导出、查看选股结果 |
| 个股 | 个股详情页 | /stocks/:symbol | 查看个股行情、财务、因子、板块、覆盖情况 |
| 板块 | 板块分析页 | /boards | 查看板块列表、板块成分、板块详情 |
| 板块 | 板块详情页 | /boards/:boardCode | 查看单个板块的成分股和统计 |
| 任务 | 任务管理页 | /jobs | 查看同步任务记录、状态、错误信息 |
| 任务 | 任务详情页 | /jobs/:jobId | 查看单次任务执行明细 |
| 覆盖 | 数据覆盖页 | /coverage | 查看股票数据覆盖范围 |
| 补数 | 补历史页 | /backfill | 触发个股补历史、查看状态 |
| 系统 | 系统设置页 | /settings | 查看系统配置、默认参数 |
| 认证 | 登录页 | /login | 系统登录（简化版token验证） |

### 第一版最小页面集合（推荐）

优先开发 6 个核心页面即可投入使用：

- `/dashboard`
- `/selection`
- `/stocks/:symbol`
- `/boards`
- `/jobs`
- `/coverage`

> 注：`/login` 作为简化版登录页，即使第一版不强制要求登录，也建议保留路由和基础 token 验证逻辑。

---

## 3. 认证与权限设计

### 3.1 简化 token 验证流程

| 流程 | 说明 |
|------|------|
| 登录 | 前端向后端 `/api/v1/auth/login` 发送用户名密码，获取 token |
| 存储 | 前端将 token 存入 localStorage |
| 请求 | 后续所有请求在 Header 中携带 `Authorization: Bearer <token>` |
| 验证 | 后端验证 token 有效性，返回用户信息 |

### 3.2 登录接口

#### POST /api/v1/auth/login

- **请求体**：

```json
{
  "username": "admin",
  "password": "xxx"
}
```

- **响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 86400,
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin"
    }
  }
}
```

### 3.3 Token 验证接口

#### GET /api/v1/auth/verify

- **说明**：前端定期调用或路由守卫中调用，验证 token 是否有效
- **响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "valid": true,
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin"
    }
  }
}
```

---

## 4. 前端路由设计

| 路由 | 页面组件 | 说明 |
|------|----------|------|
| / | Redirect | 默认跳转 /dashboard |
| /login | LoginPage | 登录页 |
| /dashboard | DashboardPage | 首页 |
| /selection | SelectionPage | 选股工作台 |
| /stocks/:symbol | StockDetailPage | 个股详情页 |
| /boards | BoardListPage | 板块列表 |
| /boards/:boardCode | BoardDetailPage | 板块详情 |
| /jobs | JobListPage | 任务管理 |
| /jobs/:jobId | JobDetailPage | 任务详情 |
| /coverage | CoveragePage | 数据覆盖 |
| /backfill | BackfillPage | 补历史 |
| /settings | SettingsPage | 系统设置 |
| /:pathMatch(.*)* | NotFoundPage | 404页面 |

---

## 5. 菜单结构建议

```
系统首页
选股工作台
板块分析
任务管理
数据覆盖
补历史（可选）
系统设置（可选）
```

> 说明：个股详情页、任务详情页、登录页不放主菜单。

---

## 6. API设计总原则

### 统一规则

- 所有接口前缀统一为：`/api/v1`
- 返回 JSON 格式
- 时间统一使用 ISO 字符串
- 日期统一格式：`YYYY-MM-DD`
- 金额单位统一：元
- 百分比字段统一：直接传百分数值（比如 5.23 表示 5.23%）
- 认证：除登录接口外，所有接口需携带有效 token

### 标准响应结构

#### 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

#### 分页响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "list": [],
    "page": 1,
    "page_size": 50,
    "total": 1200
  }
}
```

> 注意：`page_size` 默认值为 50，最大值 200。

#### 失败响应

```json
{
  "code": 1001,
  "message": "invalid parameter",
  "data": null
}
```

### 错误码规范

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1001 | 参数错误 |
| 1002 | 认证失败 / token 无效 |
| 1003 | 权限不足 |
| 2001 | 资源不存在 |
| 3001 | 服务器内部错误 |
| 4001 | 任务执行中，请稍后 |
| 4002 | 任务队列已满，请稍后重试 |

---

## 7. API清单总览

| 模块 | 接口前缀 | 用途 |
|------|----------|------|
| 认证 | /api/v1/auth | 登录、token验证 |
| Dashboard | /api/v1/dashboard | 首页摘要信息 |
| 选股 | /api/v1/selection | 选股查询 |
| 个股 | /api/v1/stocks | 个股详情相关 |
| 板块 | /api/v1/boards | 板块查询 |
| 任务 | /api/v1/jobs | 任务管理 |
| 覆盖 | /api/v1/coverage | 数据覆盖范围 |
| 补历史 | /api/v1/backfill | 补历史任务 |
| 系统 | /api/v1/system | 系统设置与元信息 |

---

## 8. Dashboard API

### 8.1 获取首页摘要

- **Method**：GET
- **Path**：/api/v1/dashboard/summary
- **认证**：需要

**返回字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| latest_trade_date | string | 最新交易日（格式 YYYY-MM-DD） |
| is_trade_day | boolean | 今天是否交易日 |
| stock_count | integer | 股票总数 |
| daily_record_count | integer | 日线记录数 |
| finance_record_count | integer | 财务记录数 |
| factor_record_count | integer | 因子记录数 |
| today_job_success_count | integer | 今日成功任务数 |
| today_job_failed_count | integer | 今日失败任务数 |
| selection_count | integer | 最新交易日选股宽表记录数 |

**示例响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "latest_trade_date": "2026-04-07",
    "is_trade_day": true,
    "stock_count": 5387,
    "daily_record_count": 2654300,
    "finance_record_count": 102340,
    "factor_record_count": 2617800,
    "today_job_success_count": 6,
    "today_job_failed_count": 1,
    "selection_count": 5231
  }
}
```

### 8.2 获取最近任务状态

- **Method**：GET
- **Path**：/api/v1/dashboard/jobs
- **认证**：需要
- **Query参数**：`limit`（整数，默认 10，最大 50）

**返回字段**：同 `/api/v1/jobs` 接口

### 8.3 获取覆盖摘要

- **Method**：GET
- **Path**：/api/v1/dashboard/coverage
- **认证**：需要

**返回字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| stocks_with_full_daily | integer | 日线覆盖完整的股票数 |
| stocks_with_full_finance | integer | 财务覆盖完整的股票数 |
| stocks_need_backfill | integer | 需要补历史的股票数 |
| total_stocks | integer | 股票总数 |

---

## 9. 选股模块API

### 9.1 获取可选交易日列表

- **Method**：GET
- **Path**：/api/v1/selection/dates
- **认证**：需要

**Query参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | string | 否 | 起始日期（YYYY-MM-DD），不传则返回最近 N 条 |
| end_date | string | 否 | 结束日期（YYYY-MM-DD） |
| limit | integer | 否 | 返回条数，默认 100，最大 500 |

> 说明：如果不传任何过滤参数，默认返回最近 100 个交易日。

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    "2026-04-07",
    "2026-04-03",
    "2026-04-02"
  ]
}
```

### 9.2 查询选股结果

- **Method**：POST
- **Path**：/api/v1/selection/query
- **认证**：需要

**请求体字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| trade_date | string | 是 | 查询交易日（YYYY-MM-DD） |
| filters | object | 否 | 筛选条件 |
| sort_by | string | 否 | 排序字段 |
| sort_order | string | 否 | asc / desc |
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页大小，默认 50，最大 200 |

**filters 字段定义**：

| 字段 | 类型 | 说明 |
|------|------|------|
| keyword | string | 股票代码或名称模糊搜索 |
| exchange | string | SH / SZ / BJ |
| industry_l1 | string | 一级行业 |
| is_st | boolean | 是否 ST（从主数据判断后返回） |
| market_value_min | number | 最小总市值（元） |
| market_value_max | number | 最大总市值（元） |
| turnover_rate_min | number | 最小换手率（%） |
| turnover_rate_max | number | 最大换手率（%） |
| roe_min | number | 最小 ROE（%） |
| roe_max | number | 最大 ROE（%） |
| revenue_yoy_min | number | 最小营收同比（%） |
| net_profit_yoy_min | number | 最小净利润同比（%） |
| is_new_high_60d | boolean | 是否 60 日新高 |
| is_break_ma20 | boolean | 是否站上 MA20 |
| trend_score_min | number | 最小趋势评分 |

**请求示例**：

```json
{
  "trade_date": "2026-04-07",
  "filters": {
    "is_st": false,
    "turnover_rate_min": 3,
    "roe_min": 10,
    "is_new_high_60d": true
  },
  "sort_by": "trend_score",
  "sort_order": "desc",
  "page": 1,
  "page_size": 50
}
```

**响应 list 字段定义**：

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | string | 股票代码（格式：600519.SH） |
| name | string | 股票名称 |
| exchange | string | 交易所（SH/SZ/BJ） |
| industry_l1 | string \| null | 一级行业 |
| close | number \| null | 收盘价（元） |
| change_pct | number \| null | 涨跌幅（%） |
| turnover_rate | number \| null | 换手率（%） |
| market_value | number \| null | 总市值（元） |
| roe | number \| null | ROE（%） |
| revenue_yoy | number \| null | 营收同比（%） |
| net_profit_yoy | number \| null | 净利润同比（%） |
| ma20 | number \| null | 20 日均线（元） |
| ma60 | number \| null | 60 日均线（元） |
| is_new_high_60d | boolean \| null | 是否 60 日新高 |
| trend_score | number \| null | 趋势评分 |
| is_st | boolean | 是否 ST（数据库中 is_st 字段） |

### 9.3 导出选股结果

- **Method**：POST
- **Path**：/api/v1/selection/export
- **认证**：需要

**请求体**：同 `/query` 接口（可不传 page 和 page_size，默认导出全部）

**响应**：

```
HTTP/1.1 200 OK
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="selection_2026-04-07.csv"

symbol,name,exchange,close,change_pct,turnover_rate,market_value,roe,revenue_yoy
600519.SH,贵州茅台,SH,1440.02,1.23,0.85,1800000000000,15.23,12.45
```

> 说明：响应直接返回 CSV 文件流，前端通过创建 Blob URL 触发下载。

---

## 10. 个股模块API

### 10.1 获取股票基础资料

- **Method**：GET
- **Path**：/api/v1/stocks/{symbol}/profile
- **认证**：需要

**路径参数**：`symbol` 格式如 `600519.SH`

**返回字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | string | 股票代码 |
| name | string | 股票名称 |
| exchange | string | 交易所 |
| ticker | string | 纯数字代码 |
| security_type | string \| null | 证券类型 |
| list_board | string \| null | 上市板块（主板/科创板/创业板等，来自 Tushare 补充） |
| list_date | string \| null | 上市日期（YYYY-MM-DD） |
| delist_date | string \| null | 退市日期，未退市则为 null |
| status | string | LISTED / DELISTED / SUSPENDED |
| is_st | boolean | 是否 ST（根据名称含 "ST" 或数据库 is_st 字段判断） |
| industry_l1 | string \| null | 一级行业 |
| industry_l2 | string \| null | 二级行业（来自 Tushare 补充） |
| area | string \| null | 地域（来自 Tushare 补充） |

### 10.2 获取股票日线行情

- **Method**：GET
- **Path**：/api/v1/stocks/{symbol}/daily
- **认证**：需要

**路径参数**：`symbol` 格式如 `600519.SH`

**Query参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | string | 否 | 开始日期（YYYY-MM-DD），不传则默认最近 120 个交易日 |
| end_date | string | 否 | 结束日期（YYYY-MM-DD） |
| limit | integer | 否 | 返回条数，默认 120，最大 730 |
| adjust | string | 否 | 复权类型：none（前复权）/ forward（后复权）/ backward（、不复权），默认 forward |

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| trade_date | string | 交易日（YYYY-MM-DD） |
| open | number | 开盘价（元） |
| high | number | 最高价（元） |
| low | number | 最低价（元） |
| close | number | 收盘价（元） |
| pre_close | number | 前收价（元） |
| change_amount | number | 涨跌额（元） |
| change_pct | number | 涨跌幅（%） |
| volume | integer | 成交量（股） |
| amount | number | 成交额（元） |
| turnover_rate | number | 换手率（%） |
| amplitude | number | 振幅（%） |
| market_value | number | 总市值（元） |
| circ_market_value | number | 流通市值（元） |

### 10.3 获取股票技术因子

- **Method**：GET
- **Path**：/api/v1/stocks/{symbol}/factors
- **认证**：需要

**路径参数**：`symbol` 格式如 `600519.SH`

**Query参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| trade_date | string | 否 | 指定交易日（YYYY-MM-DD），不传则返回最新交易日 |
| limit | integer | 否 | 返回最近 N 个交易日的技术因子，默认 60 |

> 说明：`limit` 指返回最近 N 个**交易日**的数据，不是 N 个因子字段。

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| trade_date | string | 交易日（YYYY-MM-DD） |
| ma5 | number | 5 日均线（元） |
| ma10 | number | 10 日均线（元） |
| ma20 | number | 20 日均线（元） |
| ma60 | number | 60 日均线（元） |
| rsi_6 | number | 6 日 RSI |
| rsi_14 | number | 14 日 RSI |
| atr_14 | number | 14 日 ATR |
| macd_dif | number | MACD 快线（DIF） |
| macd_dea | number | MACD 慢线（DEA） |
| macd_hist | number | MACD 柱状图（HIST = DIF - DEA） |
| is_new_high_60d | boolean | 是否 60 日新高 |
| is_break_ma20 | boolean | 是否站上 MA20 |
| trend_score | number | 趋势评分（综合指标，0-100） |

> 因子计算规则说明：
> - MA（N）：N 日简单移动平均收盘价
> - RSI（N）：N 日相对强弱指数
> - ATR（N）：N 日平均真实波幅
> - MACD：12/26/9 参数的 EMA 版本

### 10.4 获取股票财务指标

- **Method**：GET
- **Path**：/api/v1/stocks/{symbol}/finance
- **认证**：需要

**路径参数**：`symbol` 格式如 `600519.SH`

**Query参数**：`limit`（默认 8，最大 40）

> 说明：财务数据按报告期倒序返回，即最新一期在最前面。

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| report_period | string | 报告期（YYYY-MM-DD，季度末日期如 2025-03-31） |
| report_type | string | 报告类型：Q1（一季报）/ H1（半年报）/ Q3（三季报）/ FY（年报） |
| announce_date | string | 公告日期（YYYY-MM-DD） |
| eps | number \| null | 每股收益（元） |
| bps | number \| null | 每股净资产（元） |
| roe | number \| null | ROE（%） |
| gross_margin | number \| null | 毛利率（%） |
| net_margin | number \| null | 净利率（%） |
| revenue | number \| null | 营业收入（元） |
| net_profit | number \| null | 净利润（元） |
| revenue_yoy | number \| null | 营收同比（%） |
| net_profit_yoy | number \| null | 净利润同比（%） |
| ocf | number \| null | 经营现金流（元） |

### 10.5 获取股票所属板块

- **Method**：GET
- **Path**：/api/v1/stocks/{symbol}/boards
- **认证**：需要

**路径参数**：`symbol` 格式如 `600519.SH`

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| board_code | string | 板块代码 |
| board_name | string | 板块名称 |
| board_type | string | 板块类型：INDUSTRY（行业）/ CONCEPT（概念）/ INDEX（指数）/ AREA（地域） |
| update_date | string | 更新日期（YYYY-MM-DD） |

### 10.6 获取股票数据覆盖范围

- **Method**：GET
- **Path**：/api/v1/stocks/{symbol}/coverage
- **认证**：需要

**路径参数**：`symbol` 格式如 `600519.SH`

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | string | 股票代码 |
| data_type | string | 数据类型：DAILY / FINANCE / ADJUST_FACTOR |
| start_date | string \| null | 覆盖开始日期（YYYY-MM-DD） |
| end_date | string \| null | 覆盖结束日期（YYYY-MM-DD） |
| is_full_history | boolean | 是否完整历史（上市至今） |
| last_sync_at | string \| null | 最后同步时间（ISO 8601） |

---

## 11. 板块模块API

### 11.1 获取板块列表

- **Method**：GET
- **Path**：/api/v1/boards
- **认证**：需要

**Query参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| board_type | string | 否 | 板块类型：INDUSTRY / CONCEPT / INDEX / AREA，不传则返回全部 |
| keyword | string | 否 | 板块名称关键词搜索 |
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页大小，默认 50，最大 200 |

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| board_code | string | 板块代码 |
| board_name | string | 板块名称 |
| board_type | string | 板块类型 |
| member_count | integer | 成分股数量 |
| is_active | boolean | 是否活跃 |

### 11.2 获取板块详情

- **Method**：GET
- **Path**：/api/v1/boards/{boardCode}
- **认证**：需要

**路径参数**：`boardCode` 板块代码

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| board_code | string | 板块代码 |
| board_name | string | 板块名称 |
| board_type | string | 板块类型 |
| parent_board_code | string \| null | 父板块代码 |
| is_active | boolean | 是否活跃 |

### 11.3 获取板块成分股

- **Method**：GET
- **Path**：/api/v1/boards/{boardCode}/members
- **认证**：需要

**Query参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| trade_date | string | 否 | 指定交易日（YYYY-MM-DD），不传则默认最新 |
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页大小，默认 50，最大 200 |
| sort_by | string | 否 | 排序字段，默认 change_pct |
| sort_order | string | 否 | asc / desc，默认 desc |

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | string | 股票代码 |
| name | string | 股票名称 |
| exchange | string | 交易所 |
| close | number \| null | 收盘价（元） |
| change_pct | number \| null | 涨跌幅（%） |
| turnover_rate | number \| null | 换手率（%） |
| market_value | number \| null | 总市值（元） |
| trend_score | number \| null | 趋势评分 |
| industry_l1 | string \| null | 一级行业 |

> 说明：字段与选股结果表尽量对齐，便于前端复用表格组件。

---

## 12. 任务管理API

### 12.1 获取任务列表

- **Method**：GET
- **Path**：/api/v1/jobs
- **认证**：需要

**Query参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| job_name | string | 任务名（模糊匹配） |
| status | string | 任务状态：PENDING / RUNNING / SUCCESS / FAILED / CANCELLED |
| biz_date | string | 业务日期（YYYY-MM-DD） |
| page | integer | 页码，默认 1 |
| page_size | integer | 每页大小，默认 50，最大 200 |

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | integer | 任务 ID |
| job_name | string | 任务名称 |
| biz_date | string \| null | 业务日期 |
| status | string | 任务状态 |
| start_time | string | 开始时间（ISO 8601） |
| end_time | string \| null | 结束时间 |
| duration_ms | integer \| null | 耗时（毫秒） |
| rows_raw | integer \| null | 原始记录数 |
| rows_written | integer \| null | 写入记录数 |
| error_message | string \| null | 错误信息 |

### 12.2 获取任务详情

- **Method**：GET
- **Path**：/api/v1/jobs/{jobId}
- **认证**：需要

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | integer | 任务 ID |
| job_name | string | 任务名称 |
| biz_date | string \| null | 业务日期 |
| status | string | 任务状态 |
| start_time | string | 开始时间（ISO 8601） |
| end_time | string \| null | 结束时间 |
| duration_ms | integer \| null | 耗时（毫秒） |
| rows_raw | integer \| null | 原始记录数 |
| rows_written | integer \| null | 写入记录数 |
| error_message | string \| null | 错误信息 |
| created_at | string | 创建时间（ISO 8601） |
| sub_steps | array | 子步骤详情（可选） |

### 12.3 获取任务日志

- **Method**：GET
- **Path**：/api/v1/jobs/{jobId}/logs
- **认证**：需要

**Query参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| offset | integer | 日志行偏移，默认 0 |
| limit | integer | 返回条数，默认 100，最大 500 |

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "logs": [
      "[2026-04-18 10:00:00] Task started",
      "[2026-04-18 10:00:01] Fetching stock list...",
      "[2026-04-18 10:00:05] Synced 100 records"
    ],
    "total": 150,
    "offset": 0,
    "limit": 100
  }
}
```

### 12.4 手工触发任务

- **Method**：POST
- **Path**：/api/v1/jobs/run
- **认证**：需要

**请求字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| job_name | string | 是 | 任务名 |
| biz_date | string | 否 | 业务日期（YYYY-MM-DD） |
| force | boolean | 否 | 是否强制重跑（跳过检查点），默认 false |
| params | object | 否 | 附加参数 |

**请求示例**：

```json
{
  "job_name": "sync_stock_daily_job",
  "biz_date": "2026-04-07",
  "force": true,
  "params": {}
}
```

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 任务 ID |
| job_name | string | 任务名称 |
| status | string | 任务状态（通常为 PENDING 或 RUNNING） |
| queue_position | integer | 队列位置（如果排队中） |

**并发策略说明**：

- 第一版所有触发任务统一入队，串行执行
- 如果队列已满（超过 10 个待执行任务），返回错误码 `4002`
- 前端显示 "任务队列已满，请稍后重试"

### 12.5 取消任务

- **Method**：POST
- **Path**：/api/v1/jobs/{jobId}/cancel
- **认证**：需要

**说明**：仅对 PENDING 和 RUNNING 状态的任务有效，已完成的任务无法取消。

---

## 13. 数据覆盖API

### 13.1 获取覆盖列表

- **Method**：GET
- **Path**：/api/v1/coverage
- **认证**：需要

**Query参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 否 | 股票代码（精确匹配） |
| data_type | string | 否 | 数据类型：DAILY / FINANCE / ADJUST_FACTOR |
| is_full_history | boolean | 否 | 是否完整历史 |
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页大小，默认 50，最大 200 |

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | string | 股票代码 |
| name | string | 股票名称 |
| data_type | string | 数据类型 |
| start_date | string \| null | 覆盖开始日期 |
| end_date | string \| null | 覆盖结束日期 |
| is_full_history | boolean | 是否完整历史 |
| last_sync_at | string \| null | 最后同步时间 |

### 13.2 获取单只股票覆盖详情

- **Method**：GET
- **Path**：/api/v1/coverage/{symbol}
- **认证**：需要

**路径参数**：`symbol` 格式如 `600519.SH`

**响应**：返回该股票所有数据类型的覆盖情况

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "symbol": "600519.SH",
    "name": "贵州茅台",
    "coverages": [
      {
        "data_type": "DAILY",
        "start_date": "2001-08-27",
        "end_date": "2026-04-07",
        "is_full_history": true,
        "last_sync_at": "2026-04-18T08:00:00+08:00"
      },
      {
        "data_type": "FINANCE",
        "start_date": "2016-01-01",
        "end_date": "2025-12-31",
        "is_full_history": false,
        "last_sync_at": "2026-04-17T22:00:00+08:00"
      }
    ]
  }
}
```

---

## 14. 补历史API

### 14.1 触发补历史任务

- **Method**：POST
- **Path**：/api/v1/backfill/run
- **认证**：需要

**请求字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码（格式：600519.SH） |
| data_type | string | 是 | 数据类型：DAILY / FINANCE / ADJUST_FACTOR |
| start_date | string | 否 | 起始日期（YYYY-MM-DD），不传则从上市日期开始 |
| end_date | string | 否 | 结束日期（YYYY-MM-DD），不传则到最新交易日 |
| force | boolean | 否 | 是否强制覆盖已有数据，默认 false |

**请求示例**：

```json
{
  "symbol": "600519.SH",
  "data_type": "DAILY",
  "start_date": "2010-01-01",
  "end_date": "2026-04-07",
  "force": false
}
```

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 任务 ID（对应 /api/v1/jobs/{id}） |
| job_name | string | 任务名称 |
| status | string | 任务状态 |

**并发策略说明**：

- 同一只股票的同一数据类型，队列中只能有一个待执行任务
- 如果重复触发，返回 `4001` 错误码，提示 "该股票数据类型正在补数中"

### 14.2 查询补历史状态

- **Method**：GET
- **Path**：/api/v1/backfill/status/{taskId}
- **认证**：需要

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 任务 ID |
| job_name | string | 任务名称 |
| status | string | 任务状态 |
| progress | number | 进度百分比（0-100） |
| message | string | 当前步骤说明 |

---

## 15. 系统元信息API

### 15.1 获取系统配置摘要

- **Method**：GET
- **Path**：/api/v1/system/meta
- **认证**：需要

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| env | string | 运行环境：dev / test / prod |
| version | string | 系统版本 |
| db_status | string | 数据库状态：OK / ERROR |
| latest_trade_date | string | 最新交易日 |
| scheduler_status | string | 调度器状态：RUNNING / STOPPED |

---

## 16. 字段协议统一定义

### 16.1 命名规范

- 后端 JSON 字段统一使用小写下划线命名（例如：trade_date、market_value、turnover_rate）
- 前端 TypeScript 类型也建议保持一致，减少联调成本

### 16.2 日期与时间规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 日期 | YYYY-MM-DD | 2026-04-07 |
| 时间戳 | ISO 8601 | 2026-04-07T21:35:10+08:00 |

### 16.3 数值规范

| 字段类型 | 规则 |
|----------|------|
| 金额 | 单位统一为元 |
| 成交量 | 单位统一为股 |
| 百分比 | 直接传百分数，例如 5.23 表示 5.23% |
| 市值 | 单位统一为元 |
| 布尔 | true / false |

### 16.4 空值规范

- 无数据时返回 `null`
- 不要返回 `""` 表示空数字，不要返回 `"--"` 这种展示占位值，前端自己负责展示占位符

### 16.5 枚举值规范

| 类型 | 枚举值 |
|------|--------|
| 任务状态 | PENDING、RUNNING、SUCCESS、FAILED、CANCELLED |
| 数据类型 | DAILY、FINANCE、ADJUST_FACTOR、MINUTE |
| 板块类型 | INDUSTRY、CONCEPT、INDEX、AREA |
| 报告类型 | Q1、H1、Q3、FY |
| 证券状态 | LISTED、DELISTED、SUSPENDED |
| 复权类型 | none、forward、backward |

---

## 17. 技术因子字段周期定义（补充）

| 字段名 | 周期 | 计算方法 | 说明 |
|--------|------|----------|------|
| ma5 | 5 日 | 简单移动平均 | |
| ma10 | 10 日 | 简单移动平均 | |
| ma20 | 20 日 | 简单移动平均 | |
| ma60 | 60 日 | 简单移动平均 | |
| rsi_6 | 6 日 | RSI 指标 | |
| rsi_14 | 14 日 | RSI 指标 | |
| atr_14 | 14 日 | 平均真实波幅 | |
| macd_dif | 12/26 日 | 快线 EMA | |
| macd_dea | 9 日 | 慢线 EMA | |
| macd_hist | - | DIF - DEA | 柱状图值 |

---

## 18. TypeScript类型定义参考

### 18.1 通用响应类型

```typescript
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface PageResponse<T> {
  list: T[]
  page: number
  page_size: number
  total: number
}
```

### 18.2 选股结果类型

```typescript
export interface SelectionItem {
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

### 18.3 股票资料类型

```typescript
export interface StockProfile {
  symbol: string
  name: string
  exchange: string
  ticker: string
  security_type: string | null
  list_board: string | null
  list_date: string | null
  delist_date: string | null
  status: string
  is_st: boolean
  industry_l1: string | null
  industry_l2: string | null
  area: string | null
}
```

### 18.4 技术因子类型

```typescript
export interface StockFactor {
  trade_date: string
  ma5: number | null
  ma10: number | null
  ma20: number | null
  ma60: number | null
  rsi_6: number | null
  rsi_14: number | null
  atr_14: number | null
  macd_dif: number | null
  macd_dea: number | null
  macd_hist: number | null
  is_new_high_60d: boolean
  is_break_ma20: boolean
  trend_score: number | null
}
```

### 18.5 财务指标类型

```typescript
export interface FinancialIndicator {
  report_period: string
  report_type: 'Q1' | 'H1' | 'Q3' | 'FY'
  announce_date: string
  eps: number | null
  bps: number | null
  roe: number | null
  gross_margin: number | null
  net_margin: number | null
  revenue: number | null
  net_profit: number | null
  revenue_yoy: number | null
  net_profit_yoy: number | null
  ocf: number | null
}
```

### 18.6 任务类型

```typescript
export type JobStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'CANCELLED'

export interface JobItem {
  id: number
  job_name: string
  biz_date: string | null
  status: JobStatus
  start_time: string
  end_time: string | null
  duration_ms: number | null
  rows_raw: number | null
  rows_written: number | null
  error_message: string | null
}
```

---

## 19. 第一版最小可行接口集合

如果不想一上来做太多，优先开发以下 10 个接口即可实现第一版最小可用系统：

| 优先级 | 接口 | 用途 |
|--------|------|------|
| 1 | GET /api/v1/dashboard/summary | 首页摘要 |
| 2 | POST /api/v1/selection/query | 选股结果查询 |
| 3 | POST /api/v1/selection/dates | 可选交易日列表（加分页/范围参数） |
| 4 | GET /api/v1/stocks/{symbol}/profile | 个股基础资料 |
| 5 | GET /api/v1/stocks/{symbol}/daily | 个股日线（支持 K线图） |
| 6 | GET /api/v1/stocks/{symbol}/factors | 个股因子（补全周期定义） |
| 7 | GET /api/v1/stocks/{symbol}/finance | 个股财务 |
| 8 | GET /api/v1/jobs | 任务列表 |
| 9 | POST /api/v1/jobs/run | 触发任务（明确并发策略） |
| 10 | POST /api/v1/backfill/run | 触发补历史（明确队列策略） |

> 注：登录接口（`/api/v1/auth/login`）作为第一版基础设施也应该同时完成，虽然可以简化处理。

---

## 20. 后续扩展接口（预留）

以下接口在第一版后扩展：

| 接口 | 用途 | 说明 |
|------|------|------|
| GET /api/v1/boards | 板块列表 | 第一版最小系统可暂不需要 |
| GET /api/v1/boards/{boardCode}/members | 板块成分股 | 第一版最小系统可暂不需要 |
| GET /api/v1/coverage | 覆盖范围列表 | 第一版最小系统可暂不需要 |
| GET /api/v1/jobs/{id}/logs | 任务日志 | 第一版最小系统可暂不需要 |
| POST /api/v1/jobs/{id}/cancel | 取消任务 | 第一版暂不支持 |
| WebSocket /api/v1/ws/jobs | 任务状态实时推送 | 第一版用轮询替代 |
