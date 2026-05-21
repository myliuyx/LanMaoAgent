# A股股票信息缓存系统架构设计文档

## 1. 项目目标
本项目目标是搭建一套A股股票信息本地缓存与分析系统，用于每个交易日收盘后，将全市场当日股票数据同步到本地数据库，为后续选股、统计分析、因子计算、历史回测提供稳定的数据底座。

### 系统定位
| 场景 | 处理方式 |
|------|----------|
| 收盘后数据本地化 | 每天下午收盘后，定时同步全市场当日股票数据，本地保留日线、财务、复权、板块等数据 |
| 本地快速分析 | 选股逻辑尽量跑本地数据库，提高查询性能，减少频繁访问外部网站 |
| 实时数据外部获取 | 盘中行情、盘口、实时分时继续访问外部接口，避免首版系统承担过重的实时流处理复杂度 |
| 支持后续扩展 | 后续可扩展分钟线、龙虎榜、公告、资金流等数据域，支持按个股补充更长历史数据 |

---

## 2. 系统总体设计思路
整体架构采用 **离线缓存 + 本地分析 + 实时补充** 模式：
- 收盘后：把当天稳定的全市场数据同步到本地数据库
- 本地分析：选股、排名、因子计算、历史回测主要使用本地数据
- 盘中实时：实时价格、盘口、分时等高时效数据继续访问外部数据源

### 架构优势
- 查询快，不依赖外部接口做大量历史筛选
- 数据口径可控，后续策略开发更稳定
- 便于做因子预计算和快照

---

## 3. 总体架构分层
整套系统分为6个核心层级：
### 3.1 调度层
负责在指定时间触发同步任务
- 主要职责：判断是否交易日、控制任务执行顺序、控制任务重跑、记录任务状态
- 建议运行时机：
  - 收盘后15:15开始初始化
  - 15:20~18:00同步主数据、日线、估值、板块
  - 晚间同步财务及扩展数据
  - 夜间计算技术指标和选股宽表

### 3.2 采集层
负责访问外部数据源，拉取所需数据
- 主要职责：调用外部接口、处理分页、做限流和重试、做基础字段解析
- 建议按数据域拆采集器：
  - 股票主数据采集器
  - 日线行情采集器
  - 财务指标采集器
  - 复权因子采集器
  - 板块关系采集器

### 3.3 标准化处理层
负责把不同来源的数据转换成内部统一标准（非常关键的一层，避免数据库变成"接口博物馆"）
- 主要职责：
  - 股票代码标准化
  - 日期格式统一
  - 字段命名统一
  - 单位换算统一
  - 空值和异常值处理

### 3.4 数据存储层
负责把清洗后的数据写入本地数据库
- 主要职责：幂等写入、upsert更新、表间数据组织、索引管理、数据覆盖范围维护
- 推荐数据库：PostgreSQL

### 3.5 派生计算层
负责基于已落库的原始事实数据计算指标
- 主要职责：计算均线、计算涨跌幅区间值、计算RSI/MACD/ATR、生成因子表、生成选股宽表

### 3.6 查询服务层
负责给选股程序、分析脚本或后续前端提供统一查询方式
- 第一版实现：Python脚本、SQL查询、内部API模块
- 后续可扩展：FastAPI查询服务、内部策略服务、Web后台

---

## 4. 推荐技术栈
| 模块 | 推荐方案 | 说明 |
|------|----------|------|
| 编程语言 | Python | 最适合数据采集和指标计算，生态成熟，开发效率高 |
| 数据库 | PostgreSQL | 足够支撑当前规模，适合结构化查询、upsert、索引和后续扩展 |
| 定时调度 | APScheduler / cron | APScheduler比单纯cron更灵活，可以在程序内管理任务 |
| ORM/DB | SQLAlchemy + 原生SQL | 兼顾开发效率和复杂查询性能 |
| 数据处理 | Pandas | 适合批量数据转换和指标计算 |
| 部署方式 | Docker Compose | 部署方便，适合单机环境快速搭建 |
| 日志 | Python logging | 统一日志管理 |
| 配置管理 | .env + YAML | 配置和代码分离 |
| 缓存 | Redis（可选） | 后续扩展时使用 |

---

## 5. 系统模块划分
建议拆分为8个核心模块：
### 5.1 配置模块
统一管理配置项：数据库连接、数据源地址、调度时间、重试次数、限流参数、日志目录等
- 示例配置项：`DB_HOST`、`DB_PORT`、`DB_NAME`、`SYNC_TIME_DAILY_QUOTE`、`MAX_RETRY`、`REQUEST_TIMEOUT`

### 5.2 数据源客户端模块
每个外部数据源封装成独立client：`quote_client.py`、`finance_client.py`、`board_client.py`
- 职责：发送请求、返回原始数据、不在这一层做复杂业务清洗，方便后续替换数据源

### 5.3 采集器模块
对client的进一步封装，按数据主题组织：
```
security_master_collector.py
daily_quote_collector.py
adjust_factor_collector.py
financial_indicator_collector.py
board_relation_collector.py
```
- 职责：调用client拉取数据、进行分页处理、对原始数据做初步整理、输出标准数据对象

### 5.4 标准化模块
单独做`normalizer`模块
- 职责：统一symbol、统一日期、统一数值单位、统一空值、统一布尔值
- 示例：把`600519`转成`600519.SH`、把"亿元"转成"元"、把`--`转成null

### 5.5 Repository/DAO模块
封装数据库写入和查询逻辑：
```
security_master_repository.py
stock_daily_repository.py
financial_indicator_repository.py
factor_repository.py
etl_repository.py
```
- 职责：负责SQL执行、批量upsert、查询已有覆盖范围、提供统一数据库访问接口

### 5.6 Job模块
调度层调用的业务任务：
```
init_trade_day_job
sync_security_master_job
sync_stock_daily_job
sync_adjust_factor_job
sync_financial_indicator_job
compute_factor_job
build_selection_mart_job
data_quality_check_job
```
- 每个job要求：输入明确、输出明确、可单独执行、可重跑、有日志记录

### 5.7 ETL管理模块
专门处理：任务状态写入、检查点更新、覆盖范围维护、错误记录
- 作用：保证系统可追踪，不会变成"昨晚到底跑没跑成功，全靠感觉"

### 5.8 查询服务模块
- 第一版：内部查询函数
- 后续可扩展API：获取某天选股结果、获取某只股票历史日线、获取某只股票财务指标、获取板块成分股

---

## 6. 每日运行流程设计
### 6.1 步骤1：检查是否交易日
- 动作：查询`dwd_trade_calendar`，非交易日直接结束
- 建议时间：15:10

### 6.2 步骤2：初始化任务批次
- 动作：写入`etl_job_run`、设置业务日期、初始化日志上下文
- 建议时间：15:15

### 6.3 步骤3：同步股票主数据
- 同步内容：新上市股票、名称变更、ST状态变化、行业信息更新、股票状态更新
- 建议时间：15:20
- 目标表：`dwd_security_master`

### 6.4 步骤4：同步全市场日线行情
- 同步内容：开高低收、成交量、成交额、换手率、涨跌幅、市值、估值指标
- 建议时间：15:30 ~ 15:45
- 目标表：`dwd_stock_daily`

### 6.5 步骤5：同步复权因子
- 同步内容：复权因子、分红送转、除权除息事件
- 建议时间：15:45 ~ 16:00
- 目标表：`dwd_stock_adjust_factor`

### 6.6 步骤6：同步板块信息
- 同步内容：行业板块定义、概念板块定义、股票和板块的映射关系
- 建议时间：16:00 ~ 16:30
- 目标表：`dwd_board_master`、`dwd_board_relation`

### 6.7 步骤7：同步财务指标
- 同步内容：最近新增或更新的财务指标、最新报告期数据、最近公告的数据修正
- 建议时间：晚间20:00以后
- 目标表：`dwd_stock_financial_indicator`
> 注意：财务数据变化少，建议增量同步，不需要每天全量拉5年数据

### 6.8 步骤8：计算技术因子
- 计算内容：MA均线、RSI、ATR、MACD、N日涨跌幅、新高新低标记、趋势评分
- 建议时间：晚间18:00或财务同步之后统一处理
- 目标表：`dwd_stock_factor_daily`

### 6.9 步骤9：生成选股宽表
- 汇总表：`dwd_security_master`、`dwd_stock_daily`、`dwd_stock_factor_daily`、`dwd_stock_financial_indicator`、`dwd_board_relation`
- 目标表：`mart_stock_selection_daily`（选股主入口）

### 6.10 步骤10：执行数据质量检查
- 检查项：今日股票数量是否明显异常、日线数据是否有空值、`high < low`是否存在、成交量和成交额是否异常、财务数据报告期是否合理、因子表记录数是否和日线一致
- 目标：发现同步异常，避免错误数据进入选股流程

---

## 7. 初始化流程设计
系统第一次运行时单独执行
### 7.1 第一版初始化范围
- 股票主数据：全量当前
- 交易日历：全量近10年
- 全市场日线：近2年
- 复权因子：近2年
- 财务指标：近5年
- 板块主表和板块关系：当前全量

### 7.2 初始化步骤
1. 初始化基础维度：`dwd_trade_calendar`、`dwd_security_master`、`dwd_board_master`
2. 初始化全市场历史日线：`dwd_stock_daily`
3. 初始化复权因子：`dwd_stock_adjust_factor`
4. 初始化财务数据：`dwd_stock_financial_indicator`
5. 计算历史因子：`dwd_stock_factor_daily`
6. 生成最近交易日选股宽表：`mart_stock_selection_daily`
7. 写入数据覆盖范围：`etl_data_coverage`

### 7.3 初始化与日常同步的区别
| 类型 | 特点 |
|------|------|
| 初始化 | 一次性拉较长历史区间、时间跨度大、可以按股票分批执行 |
| 日常同步 | 每天只同步新增或修正数据、业务逻辑更轻、强调幂等和稳定 |

---

## 8. 项目目录结构建议
```
stock-data-platform/
├── app/
│   ├── config/
│   │   ├── settings.py
│   │   └── logging.yaml
│   ├── clients/
│   │   ├── quote_client.py
│   │   ├── finance_client.py
│   │   └── board_client.py
│   ├── collectors/
│   │   ├── security_master_collector.py
│   │   ├── daily_quote_collector.py
│   │   ├── adjust_factor_collector.py
│   │   ├── financial_indicator_collector.py
│   │   └── board_relation_collector.py
│   ├── normalizers/
│   │   ├── symbol_normalizer.py
│   │   ├── date_normalizer.py
│   │   └── unit_normalizer.py
│   ├── repositories/
│   │   ├── security_master_repository.py
│   │   ├── stock_daily_repository.py
│   │   ├── adjust_factor_repository.py
│   │   ├── financial_indicator_repository.py
│   │   ├── factor_repository.py
│   │   └── etl_repository.py
│   ├── services/
│   │   ├── factor_service.py
│   │   ├── mart_service.py
│   │   └── data_quality_service.py
│   ├── jobs/
│   │   ├── init_trade_day_job.py
│   │   ├── sync_security_master_job.py
│   │   ├── sync_stock_daily_job.py
│   │   ├── sync_adjust_factor_job.py
│   │   ├── sync_financial_indicator_job.py
│   │   ├── sync_board_relation_job.py
│   │   ├── compute_factor_job.py
│   │   ├── build_selection_mart_job.py
│   │   └── data_quality_check_job.py
│   ├── scheduler/
│   │   └── scheduler_main.py
│   ├── models/
│   │   └── dto.py
│   └── main.py
├── sql/
│   ├── ddl/
│   ├── dml/
│   └── views/
├── docs/
├── tests/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 9. 数据同步策略
按"数据域"设计，避免做成大而全脚本：
### 9.1 股票主数据同步
- 策略：每天增量刷新，如果数据源支持全量也可以每日全量覆盖小表
- 特点：数据量小、更新频率低、但非常重要

### 9.2 日线行情同步
- 策略：每日按交易日同步全市场，以`trade_date + symbol`幂等upsert
- 特点：数据量适中、是系统主数据链路

### 9.3 财务指标同步
- 策略：每日增量检查最近一段时间公告，每个季度可以增加一次全量对账任务
- 特点：低频、但可能存在修正公告

### 9.4 板块关系同步
- 策略：每日同步当前关系，历史快照按需保存
- 特点：关系型数据、板块变化不如日线频繁，但选股会用到

### 9.5 个股历史补数策略
对于重点股票，支持单独补历史：
1. 查询`etl_data_coverage`判断当前覆盖区间
2. 拉取缺失区间数据
3. upsert写入
4. 更新覆盖范围
> 优势：全市场先只保留2年，某只股票可以单独补上市以来全历史

---

## 10. 幂等、重试与异常处理
### 10.1 幂等写入
所有核心表都必须支持幂等写入：
- 日线表：主键`(trade_date, symbol)`
- 财务表：主键`(symbol, report_period, report_type)`
- 因子表：主键`(trade_date, symbol)`
- 规则：同一条数据重复同步不会产生重复记录，字段有变化可以覆盖更新

### 10.2 重试机制
对于外部接口请求：
- 单次请求失败自动重试3次
- 使用指数退避
- 对超时、连接错误、限流错误做不同处理

### 10.3 异常处理
任务失败时：
- 记录错误日志
- 写入`etl_job_run`
- 不影响无依赖的其他任务
- 支持后续单独重跑

---

## 11. 数据质量控制
### 11.1 日线质量检查
- 股票数量是否低于预期
- 是否有价格为负数
- `high < low`是否存在
- 成交量是否异常
- 停牌股票是否仍有成交量

### 11.2 财务质量检查
- 报告期是否合理
- 同一报告期是否重复
- 关键指标是否大面积空值

### 11.3 因子质量检查
- 记录数是否与日线一致
- MA计算是否空值异常
- 最新交易日指标是否完整

---

## 12. 部署方案建议
第一版推荐单机Docker Compose部署：
- 组件：app（Python应用）、postgres（数据库）、redis（可选）、scheduler（调度进程，可与app合并）
- 推荐机器配置：CPU 4核、内存8GB、SSD磁盘至少50GB（当前规模足够宽裕）

---

## 13. 第一版实施路线
分3个阶段落地，避免一开始做太大：
### 13.1 第一阶段：跑通基础链路
- 目标：数据库建好、主数据可同步、日线可同步、ETL日志可记录
- 完成内容：
  - `dwd_security_master`
  - `dwd_trade_calendar`
  - `dwd_stock_daily`
  - `etl_job_run`
  - `etl_checkpoint`

### 13.2 第二阶段：补齐分析必需数据
- 目标：支持复权和财务分析、支持个股补历史
- 完成内容：
  - `dwd_stock_adjust_factor`
  - `dwd_stock_financial_indicator`
  - `etl_data_coverage`

### 13.3 第三阶段：提升选股效率
- 目标：支持技术面快速选股、支持统一宽表查询
- 完成内容：
  - `dwd_stock_factor_daily`
  - `mart_stock_selection_daily`

---

## 14. 最终架构结论
这套系统的推荐架构可以概括为：
- 用Python + PostgreSQL搭建
- 按 **采集、标准化、入库、派生、查询** 分层
- 用APScheduler或cron做每日调度
- 用**日线 + 财务 + 复权 + 因子 + 宽表**构成本地分析底座
- 用**ETL日志、检查点、覆盖范围表**保证系统稳定运行
- 用**实时接口**补充盘中行情数据
- 用**按个股补历史机制**解决深度研究需求

---

## 15. 一句话总结
这套项目最合理的落地方式，不是做一个"每天拉接口的大脚本"，而是搭一套有调度、有分层、有幂等、有因子计算、有数据覆盖管理的本地股票数据平台。

---

## 📋 超简版执行清单
开工时可以照着这个顺序推进：
1. **建库建表**：部署PostgreSQL，执行核心DDL
2. **做初始化脚本**：初始化主数据、2年日线、5年财务、复权因子
3. **做每日同步任务**：收盘后同步当日日线、主数据增量、财务增量，计算因子，生成宽表
4. **做选股查询入口**：先直接查询`mart_stock_selection_daily`
5. **做按个股补历史**：通过`etl_data_coverage`管理覆盖范围

> 💡 准备动手写代码阶段建议：先把整个项目拆成「任务列表 + 模块清单 + 开发顺序」，每天照单推进就不会乱。