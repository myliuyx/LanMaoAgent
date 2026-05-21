# A股股票信息缓存系统 - API 接口文档

> **版本**: v0.4.2
> **Base URL**: `http://{host}:8000/api/v1`
> **Single Source of Truth** — 本文档描述所有已实现的接口

---

## 统一规范

### 响应结构

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

| code | 说明 |
|------|------|
| 0 | 成功 |
| 1001-1999 | 认证/授权错误 → HTTP 401 |
| 4001-4999 | 参数校验错误 → HTTP 400 |
| 4041-4049 | 资源不存在 → HTTP 404 |
| 5001-5999 | 服务端错误 → HTTP 500 |
| 其他 | 通用业务异常 → HTTP 200 |

### 分页结构

```json
{
  "list": [...],
  "page": 1,
  "page_size": 20,
  "total": N
}
```

### 字段命名
- 请求/响应：snake_case
- 日期格式：`YYYY-MM-DD`
- 时间戳：`YYYY-MM-DDTHH:MM:SS+08:00`

---

## 一、Auth 认证

### POST /auth/login
用户登录

**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "string"
  }
}
```

---

### GET /auth/verify
验证Token

**Headers**: `Authorization: Bearer {token}`

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "user_id": "string",
    "username": "string"
  }
}
```

---

## 二、Dashboard 仪表盘

### GET /dashboard/summary
获取首页摘要

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "latest_trade_date": "2026-04-29",
    "is_trade_day": true,
    "stock_count": 5198,
    "daily_record_count": 4865714,
    "finance_record_count": 35811,
    "factor_record_count": 1253300,
    "today_job_success_count": 5,
    "today_job_failed_count": 0,
    "selection_count": 616295
  }
}
```

---

### GET /dashboard/jobs
获取最近任务

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| limit | int | 10 | 最大50 |

**响应**: 分页列表，每项字段：
- `id`, `job_name`, `biz_date`, `status`, `start_time`, `end_time`
- `duration_ms`, `rows_raw`, `rows_written`, `error_message`

---

### GET /dashboard/coverage
获取数据覆盖摘要

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total_symbols": 5198,
    "daily_fully_covered_symbols": 5100,
    "financial_fully_covered_symbols": 3500,
    "adjust_factor_fully_covered_symbols": 0
  }
}
```

---

### POST /dashboard/watchlist-analysis
**新增 v0.3.1** 自选股技术面分析

**请求体**:
```json
{
  "symbols": ["600519.SH", "000858.SZ", "300750.SZ"]
}
```
- `symbols`: 股票代码列表，最多100个

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "summary": {
      "total": 3,
      "up_count": 1,
      "down_count": 2,
      "near_high_count": 1,
      "near_low_count": 2,
      "bullish_count": 0,
      "volume_alert_count": 1,
      "up_rate": 33.3
    },
    "stocks": [
      {
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "close": 1401.17,
        "change_pct": -0.2726,
        "turnover_rate": 0.278,
        "high_52w": 1645.0,
        "low_52w": 1322.01,
        "near_high": false,
        "near_low": true,
        "ma5": 1417.372,
        "ma10": 1418.934,
        "ma20": 1437.293,
        "ma60": 1440.5275,
        "bullish": false,
        "bearish": true,
        "volume_spike": false,
        "momentum": -3.37,
        "signals": ["均线空头排列", "接近52周低位"]
      }
    ]
  }
}
```

**字段说明**:
| 字段 | 说明 |
|------|------|
| near_high | 价格 >= 52周高价的90% |
| near_low | 价格 <= 52周低价的110% |
| bullish | MA5 > MA10 > MA20 > MA60 且 price > MA5 |
| bearish | MA5 < MA10 < MA20 < MA60 且 price < MA5 |
| volume_spike | 今日量 > 20日均量 × 2 |
| momentum | 近20日动量(%)，正=强势 |
| signals | 信号标签：均线多头/空头排列、接近52周高/低位、成交量异常放大、月动能强劲/疲弱 |

**数据来源**: dwd_stock_daily、dwd_stock_factor_daily、dwd_security_master

---

## 三、Selection 选股

### GET /selection/dates
获取可选交易日列表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| start_date | string | null | 起始日期 YYYY-MM-DD |
| end_date | string | null | 结束日期 YYYY-MM-DD |
| limit | int | 100 | 最大500 |

**响应**: `["2026-04-29", "2026-04-28", ...]`

---

### GET /selection/industries
获取可选行业列表

**响应**: `["房地产业", "金融业", "软件和信息技术服务业", ...]`

---

### GET /selection/top
**新增 v0.3.1** 选股结果Top榜

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| days | int | 5 | 统计近N个交易日，最大30 |
| limit | int | 10 | 返回Top N，最大50 |

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "symbol": "603318.SH",
      "name": "水发燃气",
      "exchange": "SH",
      "industry_l1": "燃气生产和供应业",
      "selection_count": 1,
      "avg_trend_score": 86.81,
      "avg_roe": 0.3231,
      "avg_revenue_yoy": null,
      "avg_net_profit_yoy": -49.9016,
      "high_60d_count": 0,
      "break_ma20_count": 0,
      "latest_date": "2026-04-29",
      "close": 14.55,
      "change_pct": 5.5878,
      "turnover_rate": 33.319,
      "is_new_high_60d": false,
      "is_break_ma20": false
    }
  ]
}
```

**排序规则**: 按 selection_count 降序，再按 avg_trend_score 降序

**数据来源**: mart_stock_selection_daily

---

### POST /selection/query
查询选股结果

**请求体**:
```json
{
  "trade_date": "2026-04-29",
  "filters": {
    "keyword": "茅台",
    "exchange": "SH",
    "is_st": false,
    "industry_l1": "酒",
    "market_value_min": 10000000000,
    "turnover_rate_min": 0.5,
    "roe_min": 10,
    "revenue_yoy_min": 10,
    "net_profit_yoy_min": 10,
    "is_new_high_60d": true,
    "is_break_ma20": true,
    "trend_score_min": 80
  },
  "sort_by": "trend_score",
  "sort_order": "desc",
  "page": 1,
  "page_size": 20
}
```

**响应**: 分页结构，list 每项字段：
`symbol`, `name`, `exchange`, `industry_l1`, `is_st`, `close`, `change_pct`, `turnover_rate`, `market_value`, `ma20`, `ma60`, `is_new_high_60d`, `is_break_ma20`, `roe`, `revenue_yoy`, `net_profit_yoy`, `trend_score`

---

### POST /selection/export
导出选股结果CSV

请求体同 `/selection/query`，返回 CSV 文件下载。

---

## 四、Stocks 股票

### GET /stocks/search
股票搜索

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 是 | 搜索关键词（名称或代码） |
| limit | int | 否 | 默认5，最大20 |

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {"symbol": "600519.SH", "name": "贵州茅台", "exchange": "SH"}
  ]
}
```

---

### GET /stocks/{symbol}/profile
获取股票基础信息

**路径参数**: `symbol` - 股票代码，如 `600519.SH`

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "symbol": "600519.SH",
    "ticker": "600519",
    "exchange": "SH",
    "name": "贵州茅台",
    "full_name": "贵州茅台酒股份有限公司",
    "security_type": "STOCK",
    "list_board": "主板",
    "list_date": "2001-08-27",
    "delist_date": null,
    "status": "LISTED",
    "is_st": false,
    "industry_l1": "酒、饮料和精制茶制造业",
    "industry_l2": "白酒",
    "area": "贵州"
  }
}
```

---

### GET /stocks/{symbol}/daily
获取股票日线行情

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| start_date | string | null | 起始日期 YYYY-MM-DD |
| end_date | string | null | 结束日期 YYYY-MM-DD |
| limit | int | 120 | 最大730 |
| adjust | string | qfq | none=原始价格，qfq=前复权 |

**响应**: list 每项包含 `trade_date`, `open`, `high`, `low`, `close`, `pre_close`, `change_amount`, `change_pct`, `volume`, `amount`, `turnover_rate`, `turnover_rate_f`, `amplitude`, `market_value`, `cir_market_value`, `pe_ttm`, `pb`, `ps_ttm`, `suspended_flag`, `is_limit_up`, `is_limit_down`, `adj_factor`

---

### GET /stocks/{symbol}/factors
获取股票技术因子

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| trade_date | string | null | 截止日期 YYYY-MM-DD |
| limit | int | 60 | 最大365 |

**响应**: list 每项包含 `trade_date`, `ma5/10/20/60/120/250`, `high_20/60`, `low_20/60`, `pct_5d/10d/20d/60d`, `volume_ma5/10`, `rsi_6/14`, `atr_14`, `macd_dif/dea/hist`, `is_new_high_60d`, `is_break_ma20`, `trend_score`

**数据来源**: dwd_stock_factor_daily

---

### GET /stocks/{symbol}/finance
获取股票财务指标

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| limit | int | 8 | 最大40 |

**响应**: list 每项包含 `report_period`, `report_type`, `announce_date`, `eps`, `bps`, `roe`, `roa`, `gross_margin`, `net_margin`, `debt_to_asset`, `current_ratio`, `quick_ratio`, `revenue`, `net_profit`, `revenue_yoy`, `net_profit_yoy`, `ocf`

**数据来源**: dwd_stock_financial_indicator

---

### GET /stocks/{symbol}/adjust-factor
**新增 v0.3.1** 获取股票复权因子

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| start_date | string | null | 起始日期 YYYY-MM-DD |
| end_date | string | null | 结束日期 YYYY-MM-DD |
| limit | int | 100 | 最大1000 |

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "trade_date": "2025-12-19",
      "adj_factor": 1.0,
      "forward_adj_close": 7.492,
      "backward_adj_close": 7.492,
      "cash_dividend": 23.957,
      "stock_dividend": 0.0,
      "rights_issue_ratio": null,
      "event_type": "CASH_DIVIDEND"
    }
  ]
}
```

**字段说明**:
| 字段 | 说明 |
|------|------|
| adj_factor | 复权因子 |
| forward_adj_close | 前复权收盘价 |
| backward_adj_close | 后复权收盘价 |
| cash_dividend | 每股现金分红 |
| stock_dividend | 送转股比例 |
| rights_issue_ratio | 配股比例 |
| event_type | 事件类型：CASH_DIVIDEND/ STOCK_DIVIDEND/ RIGHTS_ISSUE |

**数据来源**: dwd_stock_adjust_factor

---

### GET /stocks/{symbol}/boards
获取股票所属板块

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "board_code": "BK0438",
      "board_name": "白酒",
      "board_type": "INDUSTRY",
      "update_date": "2026-04-29"
    }
  ]
}
```

**数据来源**: dwd_board_relation + dwd_board_master

---

### GET /stocks/{symbol}/latest
获取股票最新摘要

**响应**: 合并了日线、财务、因子的最新汇总数据
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "symbol": "600519.SH",
    "name": "贵州茅台",
    "latest_trade_date": "2026-04-29",
    "close": 1401.17,
    "change_pct": -0.27,
    "turnover_rate": 0.278,
    "market_value": 1761000000000,
    "pe_ttm": 25.5,
    "pb": 5.2,
    "ma20": 1437.29,
    "ma60": 1440.53,
    "rsi_14": 45.2,
    "trend_score": 72.5,
    "roe": 32.5,
    "revenue_yoy": 15.2,
    "net_profit_yoy": 12.8
  }
}
```

---

## 五、Jobs ETL任务

### GET /jobs
获取任务列表

| 参数 | 类型 | 说明 |
|------|------|------|
| job_name | string | 任务名模糊搜索 |
| status | string | PENDING/RUNNING/SUCCESS/FAILED/CANCELLED |
| biz_date | string | 业务日期 YYYY-MM-DD |
| page | int | 默认1 |
| page_size | int | 默认20，最大200 |

---

### POST /jobs/run
手工触发任务

**请求体**:
```json
{
  "job_name": "string",
  "biz_date": "2026-04-29",
  "force": false
}
```

---

### POST /jobs/sync-daily
手动触发日线同步

| 参数 | 类型 | 说明 |
|------|------|------|
| trade_date | string | 交易日期，不传则用昨天 |
| force_restart | bool | 是否强制从头开始 |

---

### POST /jobs/sync-financial
手动触发财务指标同步

| 参数 | 类型 | 说明 |
|------|------|------|
| year | int | 年份，如 2026 |
| quarter | int | 季度 1-4 |

---

### POST /jobs/sync-factor
手动触发技术因子计算

| 参数 | 类型 | 说明 |
|------|------|------|
| trade_date | string | 交易日期，不传则计算最近5个交易日 |
| full | bool | 是否全量重算（最近2年） |

---

### POST /jobs/sync-selection
手动触发选股宽表构建

| 参数 | 类型 | 说明 |
|------|------|------|
| trade_date | string | 交易日期，不传则构建最近5个交易日 |
| full | bool | 是否全量重算（最近2年） |

---

### GET /jobs/{job_id}
获取任务详情

---

### GET /jobs/{job_id}/logs
获取任务日志

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| offset | int | 0 | 日志行偏移 |
| limit | int | 100 | 最大500 |

---

### POST /jobs/{job_id}/cancel
取消任务

---

## 六、Coverage 数据覆盖

### GET /coverage
获取覆盖列表

| 参数 | 类型 | 说明 |
|------|------|------|
| symbol | string | 股票代码过滤 |
| data_type | string | 数据类型过滤 |
| is_full_history | bool | 是否全历史覆盖 |
| page | int | 默认1 |
| page_size | int | 默认50，最大200 |

**响应**: 分页列表，每项包含覆盖的起止日期、记录数等

---

### GET /coverage/summary
获取数据覆盖摘要

---

### GET /coverage/{symbol}
获取单只股票覆盖详情

---

## 七、Boards 板块

### GET /boards
获取板块列表

| 参数 | 类型 | 说明 |
|------|------|------|
| board_type | string | INDUSTRY/CONCEPT/INDEX/AREA |
| keyword | string | 关键词搜索 |
| page | int | 默认1 |
| page_size | int | 默认50，最大200 |

**响应**: 分页列表，每项包含 `board_code`, `board_name`, `board_type`, `stock_count`

---

### GET /boards/{board_code}
获取板块详情

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "board_code": "BK0438",
    "board_name": "白酒",
    "board_type": "INDUSTRY",
    "stock_count": 20
  }
}
```

---

### GET /boards/{board_code}/members
获取板块成分股

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| trade_date | string | null | 交易日期 |
| page | int | 1 | |
| page_size | int | 50 | 最大200 |
| sort_by | string | change_pct | 排序字段 |
| sort_order | string | desc | asc/desc |

**响应**: 分页列表，每项包含成分股的基础信息和涨跌幅

---

## 八、Backfill 补历史

### POST /backfill/run
触发补历史任务

**请求体**:
```json
{
  "symbol": "600519.SH",
  "data_type": "daily",
  "start_date": "2020-01-01",
  "end_date": "2025-12-31",
  "force": false
}
```

| data_type 可选值 | 说明 |
|------------------|------|
| daily | 日线行情 |
| finance | 财务指标 |
| factor | 技术因子 |

---

### GET /backfill/status/{task_id}
查询补历史状态

---

## 九、System 系统

### GET /system/meta
获取系统配置摘要

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "env": "prod",
    "version": "0.4.2",
    "db_status": "OK",
    "latest_trade_date": "2026-04-29",
    "latest_daily_date": "2026-04-29",
    "scheduler_status": "IDLE",
    "latest_etl_status": "SUCCESS"
  }
}
```

**scheduler_status 说明**:
| 状态 | 说明 |
|------|------|
| RUNNING | 有正在执行的任务 |
| ERROR | 24小时内有失败任务 |
| IDLE | 空闲状态 |

---

## 十、Watchlist 自选股

### GET /watchlist
获取自选股列表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | |
| page_size | int | 50 | 最大200 |

**响应**: 分页列表，每项包含：
`symbol`, `name`, `exchange`, `added_at`, `close`, `change_pct`, `turnover_rate`, `trend_score`, `price_52w_high`, `price_52w_low`, `price_percentile`, `dist_to_52w_high_pct`, `dist_to_52w_low_pct`, `ma5`, `price_vs_ma5_pct`, `amplitude`, `pe_ttm`, `pb`

**数据来源**: mart_user_watchlist, dwd_security_master, dwd_stock_daily, mart_stock_selection_daily

---

### POST /watchlist
添加股票到自选

**请求体**:
```json
{
  "symbol": "600519.SH"
}
```

---

### DELETE /watchlist/{symbol}
删除自选股

---

### GET /watchlist/check/{symbol}
检查股票是否在自选列表中

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "in_watchlist": true
  }
}
```

---

## 接口统计

| Tag | 方法数 | 路径前缀 |
|-----|--------|---------|
| Auth | 2 | /api/v1/auth |
| Dashboard | 4 | /api/v1/dashboard |
| Selection | 5 | /api/v1/selection |
| Stocks | 9 | /api/v1/stocks |
| Jobs | 9 | /api/v1/jobs |
| Coverage | 3 | /api/v1/coverage |
| Boards | 3 | /api/v1/boards |
| Backfill | 2 | /api/v1/backfill |
| System | 1 | /api/v1/system |
| Watchlist | 4 | /api/v1/watchlist |
| **总计** | **42** | |

---

## Changelog

### v0.4.2
- 优化定时任务调度时间配置
- 系统元数据接口 `GET /system/meta` 新增 scheduler_status / latest_etl_status 字段

### v0.4.0
- **新增** 定时任务 `security_master_sync`（周一至周五 18:00 北京时间），每日盘前同步股票主数据
- **新增** `POST /api/v1/jobs/sync-financial` - 手动触发财务指标同步
- **新增** `POST /api/v1/jobs/sync-daily` - 手动触发日线同步
- **新增** `POST /api/v1/jobs/sync-factor` - 手动触发技术因子计算
- **新增** `POST /api/v1/jobs/sync-selection` - 手动触发选股宽表构建
- 完善 ETL 任务管理接口

### v0.3.1 (2026-04-30)
- **新增** `POST /api/v1/dashboard/watchlist-analysis` - 自选股技术面分析
- **新增** `GET /api/v1/selection/top` - 选股结果Top榜
- **新增** `GET /api/v1/stocks/{symbol}/adjust-factor` - 复权因子查询

### v0.2.3
- 完善选股查询接口
- 新增 jobs 同步触发接口

### v0.1.0
- 初始版本
