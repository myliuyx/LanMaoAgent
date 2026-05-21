# A股股票信息缓存系统表关系说明文档

## 一、整体表分类
按照设计，系统中的表一共分为4大类：

| 类别 | 作用 | 通俗理解 |
|------|------|----------|
| 维度表 | 存储基础定义信息，比如股票、交易日、板块 | 字典/主数据 |
| 事实表 | 存储每日发生的业务数据，比如日线、财务、复权 | 原始业务数据 |
| 派生表 | 存储加工后的指标和选股结果 | 为分析和选股准备的加工结果 |
| ETL 管理表 | 存储任务状态、同步进度、数据覆盖范围 | 系统运维和同步管理 |

---

## 二、所有表清单、表名及用途
### 1) 维度表（定义"谁是谁"）
#### 1. dwd_security_master
**作用**：股票主表 / 证券主数据表
- 保存每只股票的基础信息：股票代码、简称、所属交易所、上市日期、板块类型、是否ST、所属行业、地域等
- 是所有股票数据的统一主表，所有日线、财务、因子等表都通过它统一代码
- 查询股票名字、行业、市场属性都从这里获取

#### 2. dwd_trade_calendar
**作用**：交易日历表
- 保存交易所每一天是否是交易日，以及前后交易日信息
- 每日同步任务先查它判断今天要不要跑，计算均线、过去N个交易日、回测、窗口分析都依赖它

#### 3. dwd_board_master
**作用**：板块主表
- 保存板块定义信息：行业板块、概念板块、地域板块、指数成分板块等
- 统一板块字典，给板块关系表提供主数据支撑

---

### 2) 事实表（记录"每天发生了什么"）
#### 4. dwd_stock_daily
**作用**：股票日线行情表（最核心的业务表）
- 保存每只股票每个交易日的日线数据：开高低收、成交量、成交额、换手率、涨跌幅、市值、PE/PB、是否涨跌停等
- 支撑收盘后选股、历史走势查询、技术指标计算、回测基础数据，是整个系统的主干道

#### 5. dwd_stock_adjust_factor
**作用**：复权因子表
- 保存每只股票每个交易日的复权因子、分红送转相关信息：复权因子、前后复权收盘价、现金分红、送转比例、配股比例等
- 支撑前复权/后复权价格计算，让历史价格可比较，回测时避免除权除息导致价格断层

#### 6. dwd_stock_financial_indicator
**作用**：财务指标表
- 保存每只股票每个报告期的核心财务指标：EPS、BPS、ROE、ROA、毛利率、净利率、营业收入、净利润、营收/净利润同比、经营现金流等
- 支撑财务选股、财务质量分析、技术面+基本面联合筛选
> 注意：这张表不是每日一条，而是按每只股票每个报告期（季度/半年/年报）存储一条记录

#### 7. dwd_board_relation
**作用**：股票和板块的关系表
- 保存股票与板块的映射关系：比如某只股票属于哪些行业、概念、指数板块
- 支撑查询某只股票所属板块、查询某个板块包含的股票、板块联动分析、概念选股

---

### 3) 派生表（加工后的结果，为了查得更快、用得更方便）
#### 8. dwd_stock_factor_daily
**作用**：日度技术因子表
- 保存从日线行情加工出来的技术指标：MA均线、N日高低价、N日涨幅、RSI、ATR、MACD、是否创新高、趋势评分等
- 让技术选股不用每次临时计算，提升查询性能，支撑趋势类、突破类、动量类策略
> 该表由`dwd_stock_daily`计算生成

#### 9. mart_stock_selection_daily
**作用**：选股宽表（用户友好版成品表）
- 整合多表信息：股票基本信息、日线行情、财务指标、技术因子、行业属性、综合评分等
- 直接用于SQL选股、页面展示、每日选股快照、导出报表
> 设计目的是减少多表关联，实现"好查、快查、少join"

---

### 4) ETL管理表（不直接参与选股，保障系统稳定运行）
#### 10. etl_job_run
**作用**：任务运行日志表
- 保存每天各个同步任务的执行情况：任务名、开始/结束时间、是否成功、写入行数、错误信息等
- 用于追踪任务状态、排查失败原因

#### 11. etl_checkpoint
**作用**：同步检查点表
- 记录某个任务当前同步到的位置：比如增量任务同步到的日期、分页接口同步到的页码、某类数据同步到的报告期等
- 支持断点续跑，避免重复拉全量，支撑增量同步

#### 12. etl_data_coverage
**作用**：数据覆盖范围表
- 记录每只股票某类数据的覆盖时间范围：比如某只股票的日线已经覆盖到哪天、财务数据从哪年开始、是否补全上市以来全量数据等
- 支撑"按个股补历史"的需求，判断某只股票是否需要补数据

---

## 三、表之间的关联关系
### 1. 核心主线关系
```
dwd_security_master（定义股票身份）
        ↓
dwd_stock_daily（记录每日行情）
        ↓
dwd_stock_factor_daily（计算技术指标）
        ↓
mart_stock_selection_daily（拼成选股成品表）
```
这是整个系统最重要的数据流链条。

### 2. 财务关系线
```
dwd_security_master
        ↓
dwd_stock_financial_indicator（按报告期存财务数据）
        ↓
mart_stock_selection_daily（映射最新财务数据到每日宽表）
```
财务表本身不是每日一条，会取最近已披露的报告期数据映射到当日选股宽表中。

### 3. 复权关系线
```
dwd_security_master
        ↓
dwd_stock_daily ←→ dwd_stock_adjust_factor
```
通过`(symbol, trade_date)`关联，用于计算前后复权价格，如果复权因子已经冗余在日线表中可以省略关联。

### 4. 板块关系线
```
dwd_board_master（定义板块）
        ↑
dwd_board_relation（多对多关联）
        ↓
dwd_security_master（定义股票）
```
一只股票可以属于多个板块，一个板块可以包含多只股票，通过中间表实现多对多关联。

### 5. ETL管理关系线
ETL三张表和业务表是管理型关系，不是查询关联关系：
- `etl_job_run`：记录同步任务执行状态
- `etl_checkpoint`：记录同步进度
- `etl_data_coverage`：记录单只股票的数据完整度

---

## 四、整体关系图
```
                     +----------------------+
                     | dwd_trade_calendar   |
                     | 交易日历表           |
                     +----------------------+

+----------------------+       +----------------------+
| dwd_security_master  |       | dwd_board_master     |
| 股票主数据表         |       | 板块主表             |
+----------------------+       +----------------------+
           |                              ^
           |                              |
           v                              |
+----------------------+       +----------------------+
| dwd_stock_daily      |<----->| dwd_board_relation   |
| 股票日线行情表       |       | 股票板块关系表       |
+----------------------+       +----------------------+
           |
           |<--------------------+
           |                     |
           v                     |
+----------------------+         |
| dwd_stock_adjust_    |         |
| factor               |         |
| 复权因子表           |         |
+----------------------+         |
           |                     |
           v                     |
+----------------------+         |
| dwd_stock_factor_    |         |
| daily                |         |
| 日度技术因子表       |         |
+----------------------+         |
           |                     |
           +----------+----------+
                      |
                      v
+----------------------+
| mart_stock_selection |
| _daily               |
| 选股宽表             |
+----------------------+
          ^
          |
+----------------------+
| dwd_stock_financial_ |
| indicator            |
| 财务指标表           |
+----------------------+

+----------------------+
| etl_job_run          |
| 任务运行日志表       |
+----------------------+

+----------------------+
| etl_checkpoint       |
| 任务检查点表         |
+----------------------+

+----------------------+
| etl_data_coverage    |
| 数据覆盖范围表       |
+----------------------+
```

---

## 五、表关联速查表
| 表名 | 类型 | 主要用途 | 主要关联对象 |
|------|------|----------|--------------|
| dwd_security_master | 维度表 | 股票基础信息 | 所有股票相关表 |
| dwd_trade_calendar | 维度表 | 交易日定义 | 同步任务、回测、窗口计算 |
| dwd_board_master | 维度表 | 板块定义 | dwd_board_relation |
| dwd_stock_daily | 事实表 | 日线行情 | dwd_security_master、dwd_stock_adjust_factor、dwd_stock_factor_daily |
| dwd_stock_adjust_factor | 事实表 | 复权因子 | dwd_stock_daily |
| dwd_stock_financial_indicator | 事实表 | 财务指标 | dwd_security_master、mart_stock_selection_daily |
| dwd_board_relation | 事实表 | 股票与板块映射 | dwd_security_master、dwd_board_master |
| dwd_stock_factor_daily | 派生表 | 技术因子 | dwd_stock_daily |
| mart_stock_selection_daily | 派生表 | 选股宽表 | 日线、财务、因子、主数据 |
| etl_job_run | 管理表 | 任务日志 | ETL任务 |
| etl_checkpoint | 管理表 | 同步进度 | ETL任务 |
| etl_data_coverage | 管理表 | 数据覆盖范围 | 按股票的数据同步状态 |

---

## 六、核心表优先级
### 第一核心层（地基）
- dwd_security_master
- dwd_stock_daily

### 第二核心层（分析补充）
- dwd_stock_adjust_factor
- dwd_stock_financial_indicator

### 第三核心层（易用性优化）
- dwd_stock_factor_daily
- mart_stock_selection_daily

### 保障层（可维护性）
- etl_job_run
- etl_checkpoint
- etl_data_coverage

---

## 七、业务视角理解
- `dwd_security_master`：回答「这只股票是谁」
- `dwd_stock_daily`：回答「这只股票今天表现怎样」
- `dwd_stock_adjust_factor`：回答「历史价格该怎么正确还原」
- `dwd_stock_financial_indicator`：回答「这家公司基本面怎么样」
- `dwd_board_relation`：回答「它属于哪些板块」
- `dwd_stock_factor_daily`：回答「它的技术形态和因子值怎样」
- `mart_stock_selection_daily`：回答「我今天要不要选它」
- `etl_*`表：回答「系统昨天晚上有没有老老实实干活」

---

## 八、超短记忆版
```
主数据：
- dwd_security_master：股票字典
- dwd_trade_calendar：交易日字典
- dwd_board_master：板块字典

核心数据：
- dwd_stock_daily：每日行情
- dwd_stock_adjust_factor：复权因子
- dwd_stock_financial_indicator：财务指标
- dwd_board_relation：股票-板块关系

分析数据：
- dwd_stock_factor_daily：技术指标
- mart_stock_selection_daily：选股宽表

系统管理：
- etl_job_run：任务日志
- etl_checkpoint：同步进度
- etl_data_coverage：数据覆盖情况
```

---

### 一句话总结
这套表的关系本质上是：用`dwd_security_master`定义股票，用`dwd_stock_daily`和`dwd_stock_financial_indicator`存核心事实，用`dwd_stock_factor_daily`和`mart_stock_selection_daily`提供高效选股能力，再用`etl_*`表保证整套系统可同步、可追踪、可补历史。
