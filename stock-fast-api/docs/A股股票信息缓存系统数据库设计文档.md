# A股股票信息缓存系统数据库设计文档

## 1. 文档目的
本文档用于定义 A 股股票信息缓存系统的数据库设计方案，支撑以下核心目标：

- 每个交易日收盘后，将当日全市场股票数据同步到本地数据库
- 为选股、统计分析、因子计算、回测提供本地数据支持
- 支持后续按个股补充更长历史数据
- 支持未来扩展分钟线、资金流、龙虎榜、公告等数据域
- 保证数据结构统一、可维护、可扩展、可重跑

本文档主要覆盖：
- 数据分层设计
- 表结构设计
- 主键与索引规则
- 数据字段规范
- ETL 支撑表设计
- 第一版最小可行建表范围

## 2. 系统设计目标
本地数据库不是单纯的数据缓存仓库，而是系统的分析底座。设计时需要满足以下要求：

### 2.1 业务目标
支持以下场景：
- 全市场日常选股
  - 收盘后条件筛选
  - 技术指标筛选
  - 财务指标筛选
  - 综合打分与排名
- 个股深度分析
  - 按股票补充更长周期历史数据
  - 补充上市以来日线
  - 未来扩展分钟线和公告
- 数据同步与维护
  - 每日定时同步
  - 支持失败重跑
  - 支持数据校验
  - 支持覆盖范围跟踪

### 2.2 技术目标
数据库设计需满足：
- 统一证券代码格式
- 统一时间维度命名
- 统一单位标准
- 支持幂等写入
- 支持快速查询
- 支持后续派生宽表与指标表

## 3. 数据分层设计
推荐采用三层模型：

### 3.1 原始层 Raw
用于保存外部接口原始返回数据，便于：
- 问题排查
- 字段回溯
- 数据源变化跟踪

表命名建议：
- `raw_api_daily_quote`
- `raw_api_finance_indicator`

第一版可选，不强制全部落地。

### 3.2 标准化层 Staging
用于将不同来源的数据统一格式，包括：
- 代码格式统一
- 日期格式统一
- 字段名统一
- 单位统一

表命名建议：
- `stg_stock_daily`
- `stg_stock_financial_indicator`

第一版可以由程序内存转换后直接写正式表，不一定必须落地独立 staging 表。

### 3.3 服务层 DWD / MART
正式分析查询层。
- `dwd_*`：标准明细事实表、维度表
- `mart_*`：选股宽表、聚合表、专题表

这是系统最重要的层。

## 4. 命名规范
### 4.1 表命名规范
统一使用小写下划线命名。

前缀建议：
- `dwd_`：明细层正式表
- `mart_`：面向分析或选股的宽表
- `etl_`：同步管理表
- `raw_`：原始数据表
- `stg_`：标准化中间表

示例：
- `dwd_security_master`
- `dwd_stock_daily`
- `dwd_stock_financial_indicator`
- `mart_stock_selection_daily`
- `etl_job_run`

### 4.2 字段命名规范
统一使用英文小写下划线命名。

常用字段命名约定：
- `symbol`：标准股票代码
- `trade_date`：交易日期
- `report_period`：报告期
- `announce_date`：公告日期
- `created_at`：创建时间
- `updated_at`：更新时间
- `source`：数据来源

## 5. 统一数据标准
### 5.1 股票代码标准
内部统一使用以下格式：
- 600519.SH
- 000001.SZ
- 430047.BJ

要求：
- 所有事实表和维度表统一使用 `symbol`
- 外部接口编码在采集阶段转换
- 不允许正式表中混用 `sh600519`、`600519`、`SHSE.600519`

### 5.2 日期标准
统一字段命名：
- 交易日：`trade_date`
- 报告期：`report_period`
- 公告日：`announce_date`
- 业务日期：`biz_date`

日期类型建议：
- 日期使用 `date`
- 时间使用 `timestamp`

### 5.3 单位标准
统一单位如下：
- `volume`：股
- `amount`：元
- `market_value`：元
- `circulating_market_value`：元
- `revenue`：元
- `net_profit`：元

### 5.4 百分比字段标准
所有百分比字段统一直接存百分数值：
- 5.23 表示 5.23%
- -3.15 表示 -3.15%

不得有的字段按 0.0523 存，有的字段按 5.23 存。

## 6. 核心表设计概览
第一版推荐的核心表如下：

### 6.1 维度表
- `dwd_security_master`
- `dwd_trade_calendar`
- `dwd_board_master`

### 6.2 事实表
- `dwd_stock_daily`
- `dwd_stock_adjust_factor`
- `dwd_stock_financial_indicator`
- `dwd_board_relation`

### 6.3 派生表
- `dwd_stock_factor_daily`
- `mart_stock_selection_daily`

### 6.4 ETL 管理表
- `etl_job_run`
- `etl_checkpoint`
- `etl_data_coverage`

## 7. 表结构设计
### 7.1 股票主数据表 dwd_security_master
#### 7.1.1 作用
用于维护股票基础信息，是全系统股票维度主表。所有行情表、财务表、因子表都通过 `symbol` 与本表关联。

#### 7.1.2 主键
`symbol`

#### 7.1.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| symbol | varchar(16) | 标准股票代码，如 600519.SH |
| ticker | varchar(8) | 纯数字代码，如 600519 |
| exchange | varchar(8) | 交易所：SH / SZ / BJ |
| name | varchar(64) | 股票简称 |
| full_name | varchar(128) | 公司全称 |
| security_type | varchar(32) | 股票类型，如主板、创业板、科创板、北交所 |
| list_board | varchar(32) | 上市板块 |
| list_date | date | 上市日期 |
| delist_date | date | 退市日期 |
| status | varchar(16) | LISTED / DELISTED / SUSPENDED |
| is_st | boolean | 是否 ST |
| industry_l1 | varchar(64) | 一级行业 |
| industry_l2 | varchar(64) | 二级行业 |
| area | varchar(64) | 所属地域 |
| currency | varchar(8) | 币种，默认 CNY |
| source | varchar(32) | 数据来源 |
| updated_at | timestamp | 更新时间 |

#### 7.1.4 索引建议
- 主键：`symbol`
- 唯一索引：`(ticker, exchange)`

---

### 7.2 交易日历表 dwd_trade_calendar
#### 7.2.1 作用
用于管理交易日信息，支撑：
- 判断是否交易日
- 获取上一交易日和下一交易日
- 同步调度和回测窗口计算

#### 7.2.2 主键
`(exchange, trade_date)`

#### 7.2.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| exchange | varchar(8) | SH / SZ / BJ |
| trade_date | date | 日期 |
| is_open | boolean | 是否交易日 |
| prev_trade_date | date | 前一交易日 |
| next_trade_date | date | 下一交易日 |
| week_no | int | 年内第几周 |
| month_no | int | 月份 |
| quarter_no | int | 季度 |
| year_no | int | 年份 |
| updated_at | timestamp | 更新时间 |

---

### 7.3 股票日线行情表 dwd_stock_daily
#### 7.3.1 作用
用于保存全市场日线行情，是选股、分析、回测的基础事实表。

#### 7.3.2 主键
`(trade_date, symbol)`

#### 7.3.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| trade_date | date | 交易日 |
| symbol | varchar(16) | 股票代码 |
| open | numeric(18,4) | 开盘价 |
| high | numeric(18,4) | 最高价 |
| low | numeric(18,4) | 最低价 |
| close | numeric(18,4) | 收盘价 |
| pre_close | numeric(18,4) | 前收盘价 |
| change_amount | numeric(18,4) | 涨跌额 |
| change_pct | numeric(10,4) | 涨跌幅 |
| volume | bigint | 成交量，单位股 |
| amount | numeric(20,2) | 成交额，单位元 |
| amplitude | numeric(10,4) | 振幅 |
| turnover_rate | numeric(10,4) | 换手率 |
| turnover_rate_f | numeric(10,4) | 自由流通换手率 |
| volume_ratio | numeric(10,4) | 量比 |
| market_value | numeric(20,2) | 总市值 |
| circulating_market_value | numeric(20,2) | 流通市值 |
| pe_ttm | numeric(18,4) | 市盈率 TTM |
| pb | numeric(18,4) | 市净率 |
| ps_ttm | numeric(18,4) | 市销率 TTM |
| suspended_flag | boolean | 是否停牌 |
| is_limit_up | boolean | 是否涨停 |
| is_limit_down | boolean | 是否跌停 |
| adj_factor | numeric(18,8) | 复权因子，可冗余保存 |
| source | varchar(32) | 数据来源 |
| created_at | timestamp | 创建时间 |
| updated_at | timestamp | 更新时间 |

#### 7.3.4 索引建议
- 主键：`(trade_date, symbol)`
- 普通索引：`(symbol, trade_date desc)`
- 普通索引：`(trade_date)`

#### 7.3.5 设计说明
- volume 统一为股
- amount 统一为元
- 百分比字段直接存百分数值
- adj_factor 可冗余保存，便于查询时少关联一张表

---

### 7.4 复权因子表 dwd_stock_adjust_factor
#### 7.4.1 作用
用于保存复权因子和分红送转相关信息，支撑：
- 前复权价格计算
- 后复权价格计算
- 回测处理
- 除权除息事件分析

#### 7.4.2 主键
`(trade_date, symbol)`

#### 7.4.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| trade_date | date | 交易日 |
| symbol | varchar(16) | 股票代码 |
| adj_factor | numeric(18,8) | 复权因子 |
| forward_adj_close | numeric(18,4) | 前复权收盘价，可选 |
| backward_adj_close | numeric(18,4) | 后复权收盘价，可选 |
| cash_dividend | numeric(18,4) | 每股现金分红 |
| stock_dividend | numeric(18,4) | 送转股比例 |
| rights_issue_ratio | numeric(18,4) | 配股比例 |
| event_type | varchar(32) | 事件类型 |
| source | varchar(32) | 数据来源 |
| updated_at | timestamp | 更新时间 |

---

### 7.5 财务指标表 dwd_stock_financial_indicator
#### 7.5.1 作用
用于保存最常用的财务分析指标宽表。第一版优先建设该表，不强制一开始就建立完整三大报表表结构。

#### 7.5.2 主键
`(symbol, report_period, report_type)`

#### 7.5.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| symbol | varchar(16) | 股票代码 |
| report_period | date | 报告期 |
| report_type | varchar(16) | Q1 / H1 / Q3 / FY |
| announce_date | date | 公告日期 |
| eps | numeric(18,4) | 每股收益 |
| bps | numeric(18,4) | 每股净资产 |
| roe | numeric(10,4) | 净资产收益率 |
| roa | numeric(10,4) | 总资产收益率 |
| gross_margin | numeric(10,4) | 毛利率 |
| net_margin | numeric(10,4) | 净利率 |
| debt_to_asset | numeric(10,4) | 资产负债率 |
| current_ratio | numeric(10,4) | 流动比率 |
| quick_ratio | numeric(10,4) | 速动比率 |
| revenue | numeric(20,2) | 营业收入 |
| net_profit | numeric(20,2) | 净利润 |
| revenue_yoy | numeric(10,4) | 营收同比 |
| net_profit_yoy | numeric(10,4) | 净利润同比 |
| ocf | numeric(20,2) | 经营现金流 |
| ocf_to_revenue | numeric(10,4) | 经营现金流/营收 |
| source | varchar(32) | 数据来源 |
| updated_at | timestamp | 更新时间 |

#### 7.5.4 索引建议
- 主键：`(symbol, report_period, report_type)`
- 普通索引：`(report_period desc)`
- 普通索引：`(announce_date desc)`

---

### 7.6 板块主表 dwd_board_master
#### 7.6.1 作用
用于统一板块定义，支持：
- 行业板块
- 概念板块
- 地域板块
- 指数成分板块

#### 7.6.2 主键
`board_code`

#### 7.6.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| board_code | varchar(32) | 板块代码 |
| board_name | varchar(128) | 板块名称 |
| board_type | varchar(32) | INDUSTRY / CONCEPT / AREA / INDEX |
| parent_board_code | varchar(32) | 上级板块代码 |
| is_active | boolean | 是否有效 |
| source | varchar(32) | 数据来源 |
| updated_at | timestamp | 更新时间 |

---

### 7.7 股票板块关系表 dwd_board_relation
#### 7.7.1 作用
用于记录股票与板块之间的关系。

#### 7.7.2 主键
`(trade_date, symbol, board_code)`

#### 7.7.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| trade_date | date | 快照日期 |
| symbol | varchar(16) | 股票代码 |
| board_code | varchar(32) | 板块代码 |
| board_type | varchar(32) | 板块类型 |
| relation_source | varchar(32) | 来源 |
| updated_at | timestamp | 更新时间 |

---

### 7.8 日度技术因子表 dwd_stock_factor_daily
#### 7.8.1 作用
用于预计算技术指标和趋势因子，减少查询时的复杂计算。

#### 7.8.2 主键
`(trade_date, symbol)`

#### 7.8.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| trade_date | date | 交易日 |
| symbol | varchar(16) | 股票代码 |
| ma5 | numeric(18,4) | 5日均线 |
| ma10 | numeric(18,4) | 10日均线 |
| ma20 | numeric(18,4) | 20日均线 |
| ma60 | numeric(18,4) | 60日均线 |
| ma120 | numeric(18,4) | 120日均线 |
| ma250 | numeric(18,4) | 250日均线 |
| high_20 | numeric(18,4) | 20日最高价 |
| high_60 | numeric(18,4) | 60日最高价 |
| low_20 | numeric(18,4) | 20日最低价 |
| low_60 | numeric(18,4) | 60日最低价 |
| pct_5d | numeric(10,4) | 5日涨幅 |
| pct_10d | numeric(10,4) | 10日涨幅 |
| pct_20d | numeric(10,4) | 20日涨幅 |
| pct_60d | numeric(10,4) | 60日涨幅 |
| volume_ma5 | numeric(20,2) | 5日均量 |
| volume_ma10 | numeric(20,2) | 10日均量 |
| rsi_6 | numeric(10,4) | RSI(6) |
| rsi_14 | numeric(10,4) | RSI(14) |
| atr_14 | numeric(18,4) | ATR(14) |
| macd_dif | numeric(18,4) | MACD DIF |
| macd_dea | numeric(18,4) | MACD DEA |
| macd_hist | numeric(18,4) | MACD 柱状图 |
| is_new_high_60d | boolean | 是否创60日新高 |
| is_break_ma20 | boolean | 是否突破20日均线 |
| trend_score | numeric(10,4) | 趋势评分 |
| updated_at | timestamp | 更新时间 |

#### 7.8.4 索引建议
- 主键：`(trade_date, symbol)`
- 普通索引：`(symbol, trade_date desc)`

---

### 7.9 选股宽表 mart_stock_selection_daily
#### 7.9.1 作用
用于选股和分析的宽表，汇总行情 + 因子 + 财务数据，一次查询可完成多维度筛选。

#### 7.9.2 主键
`(trade_date, symbol)`

#### 7.9.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| trade_date | date | 交易日 |
| symbol | varchar(16) | 股票代码 |
| name | varchar(64) | 股票简称 |
| exchange | varchar(8) | 交易所 |
| security_type | varchar(32) | 股票类型 |
| is_st | boolean | 是否ST |
| close_price | numeric(18,4) | 收盘价 |
| change_pct | numeric(10,4) | 涨跌幅 |
| volume_ratio | numeric(10,4) | 量比 |
| turnover_rate_f | numeric(10,4) | 自由流通换手率 |
| amplitude | numeric(10,4) | 振幅 |
| market_value | numeric(20,2) | 总市值 |
| circulating_market_value | numeric(20,2) | 流通市值 |
| pe_ttm | numeric(18,4) | 市盈率TTM |
| pb | numeric(18,4) | 市净率 |
| ps_ttm | numeric(18,4) | 市销率TTM |
| ma5 | numeric(18,4) | 5日均线 |
| ma10 | numeric(18,4) | 10日均线 |
| ma20 | numeric(18,4) | 20日均线 |
| ma60 | numeric(18,4) | 60日均线 |
| rsi_14 | numeric(10,4) | RSI(14) |
| macd_dif | numeric(18,4) | MACD DIF |
| macd_dea | numeric(18,4) | MACD DEA |
| macd_hist | numeric(18,4) | MACD 柱状图 |
| is_new_high_60d | boolean | 是否创60日新高 |
| is_break_ma20 | boolean | 是否突破20日均线 |
| trend_score | numeric(10,4) | 趋势评分 |
| roe | numeric(10,4) | 净资产收益率 |
| roa | numeric(10,4) | 总资产收益率 |
| gross_margin | numeric(10,4) | 毛利率 |
| net_margin | numeric(10,4) | 净利率 |
| debt_to_asset | numeric(10,4) | 资产负债率 |
| revenue_yoy | numeric(10,4) | 营收同比 |
| net_profit_yoy | numeric(10,4) | 净利润同比 |
| board_codes | varchar(512) | 板块代码（逗号分隔） |
| board_names | varchar(512) | 板块名称（逗号分隔） |
| industry_l1 | varchar(64) | 一级行业 |
| industry_l2 | varchar(64) | 二级行业 |
| area | varchar(64) | 所属地域 |
| is_limit_up | boolean | 是否涨停 |
| is_limit_down | boolean | 是否跌停 |
| suspended_flag | boolean | 是否停牌 |
| composite_score | numeric(10,4) | 综合评分 |
| rank_pct | numeric(10,4) | 排名百分位 |
| updated_at | timestamp | 更新时间 |

#### 7.9.4 索引建议
- 主键：`(trade_date, symbol)`
- 普通索引：`(symbol)`
- 普通索引：`(trade_date)`

---

### 7.10 用户自选股表 mart_user_watchlist
#### 7.10.1 作用
用于保存用户的自选股列表。

#### 7.10.2 主键
`id`

#### 7.10.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| id | bigserial | 自增主键 |
| user_id | varchar(64) | 用户ID |
| symbol | varchar(16) | 股票代码 |
| added_at | timestamp | 添加时间 |

#### 7.10.4 索引建议
- 主键：`(id)`
- 唯一索引：`(user_id, symbol)`
- 普通索引：`(user_id)`

---

## 8. ETL 管理表设计

### 8.1 任务运行表 etl_job_run
#### 8.1.1 作用
记录每次 ETL 任务的执行情况，支持审计和问题排查。

#### 8.1.2 主键
`id`

#### 8.1.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| id | bigserial | 主键 |
| job_name | varchar(64) | 任务名称 |
| biz_date | date | 业务日期 |
| status | varchar(16) | 状态（PENDING/RUNNING/SUCCESS/FAILED） |
| start_time | timestamp | 开始时间 |
| end_time | timestamp | 结束时间 |
| duration_ms | bigint | 耗时（毫秒） |
| rows_raw | int | 原始记录数 |
| rows_written | int | 写入记录数 |
| error_message | text | 错误信息 |
| created_at | timestamp | 创建时间 |

#### 8.1.4 索引建议
- 主键：`(id)`
- 普通索引：`(job_name, biz_date)`
- 普通索引：`(status)`

---

### 8.2 检查点表 etl_checkpoint
#### 8.2.1 作用
支持断点续传，记录任务执行进度。

#### 8.2.2 主键
`(job_name, checkpoint_key)`

#### 8.2.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| job_name | varchar(64) | 任务名称 |
| checkpoint_key | varchar(64) | 检查点键 |
| checkpoint_value | varchar(128) | 检查点值 |
| updated_at | timestamp | 更新时间 |

---

### 8.3 数据覆盖表 etl_data_coverage
#### 8.3.1 作用
跟踪每只股票各类型数据的覆盖范围。

#### 8.3.2 主键
`(symbol, data_type)`

#### 8.3.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| symbol | varchar(16) | 股票代码 |
| data_type | varchar(32) | 数据类型（DAILY/FINANCE/FACTOR） |
| start_date | date | 数据起始日期 |
| end_date | date | 数据结束日期 |
| is_full_history | boolean | 是否完整历史 |
| last_sync_at | timestamp | 最后同步时间 |
| updated_at | timestamp | 更新时间 |

---

### 8.4 补历史任务表 etl_backfill_task
#### 8.4.1 作用
记录补历史任务的执行状态。

#### 8.4.2 主键
`id`

#### 8.4.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| id | bigserial | 主键 |
| symbol | varchar(16) | 股票代码 |
| data_type | varchar(32) | 数据类型 |
| start_date | date | 起始日期 |
| end_date | date | 结束日期 |
| status | varchar(16) | 状态 |
| progress | int | 进度（0-100） |
| rows_written | int | 写入记录数 |
| error_message | text | 错误信息 |
| force | boolean | 是否强制重跑 |
| created_at | timestamp | 创建时间 |
| updated_at | timestamp | 更新时间 |

#### 8.4.4 索引建议
- 主键：`(id)`
- 普通索引：`(symbol)`
- 普通索引：`(status)`
- 普通索引：`(created_at desc)`

---

### 8.5 任务日志表 etl_job_run_log
#### 8.5.1 作用
存储 ETL 任务执行过程中的详细日志。

#### 8.5.2 主键
`id`

#### 8.5.3 字段定义
| 字段名 | 类型 | 说明 |
|-------|------|------|
| id | bigserial | 主键 |
| job_id | int | 任务ID |
| level | varchar(16) | 日志级别（INFO/WARN/ERROR） |
| message | text | 日志内容 |
| created_at | timestamp | 创建时间 |

#### 8.5.4 索引建议
- 主键：`(id)`
- 普通索引：`(job_id)`
- 普通索引：`(created_at)`

---

## 9. 表关系总结

### 9.1 核心表关系图

```
dwd_security_master (主键: symbol)
    │
    ├── dwd_stock_daily (外键: symbol)
    ├── dwd_stock_adjust_factor (外键: symbol)
    ├── dwd_stock_financial_indicator (外键: symbol)
    ├── dwd_stock_factor_daily (外键: symbol)
    ├── mart_stock_selection_daily (外键: symbol)
    └── dwd_board_relation (外键: symbol)

dwd_trade_calendar (主键: exchange, trade_date)
    └── 被各任务引用判断是否为交易日

dwd_board_master (主键: board_code)
    │
    └── dwd_board_relation (外键: board_code)
```

### 9.2 派生出表关系

```
dwd_stock_daily + dwd_stock_factor_daily + dwd_stock_financial_indicator
    │
    └── mart_stock_selection_daily（选股宽表，汇总以上所有表的数据）
```

---

## 10. 相关文档

- [表关系说明文档](A股股票信息缓存系统表关系说明文档.md)
- [REGISTRY.md（API接口）](../stock-fast-api/docs/REGISTRY.md)
- [定时任务使用文档](定时任务使用文档.md)
- [DDL脚本](../09_postgresql_ddl.sql)