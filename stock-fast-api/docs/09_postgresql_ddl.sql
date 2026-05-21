-- A股股票信息缓存系统 - PostgreSQL DDL
-- 生成时间: 2026-04-30
-- 数据库: stock_cache_system
-- 共 14 张表

-- =============================================
-- 1. 用户认证表 app_user
-- =============================================
create table if not exists app_user (
    id bigserial primary key,
    username varchar(50) unique not null,
    password_hash varchar(255) not null,
    role varchar(20) default 'viewer',
    is_active boolean default true,
    created_at timestamp not null default now(),
    updated_at timestamp not null default now()
);

-- =============================================
-- 2. 股票主数据表 dwd_security_master
-- =============================================
create table if not exists dwd_security_master (
    symbol varchar(16) primary key,
    ticker varchar(8) not null,
    exchange varchar(8) not null,
    name varchar(64) not null,
    full_name varchar(128),
    security_type varchar(32),
    list_board varchar(32),
    list_date date,
    delist_date date,
    status varchar(16) not null default 'LISTED',
    is_st boolean not null default false,
    industry_l1 varchar(64),
    industry_l2 varchar(64),
    area varchar(64),
    currency varchar(8) default 'CNY',
    source varchar(32),
    updated_at timestamp not null default now()
);

create unique index if not exists uk_security_master_ticker_exchange
on dwd_security_master (ticker, exchange);

-- =============================================
-- 3. 交易日历表 dwd_trade_calendar
-- =============================================
create table if not exists dwd_trade_calendar (
    exchange varchar(8) not null,
    trade_date date not null,
    is_open boolean not null,
    prev_trade_date date,
    next_trade_date date,
    week_no int,
    month_no int,
    quarter_no int,
    year_no int,
    updated_at timestamp not null default now(),
    primary key (exchange, trade_date)
);

-- =============================================
-- 4. 股票日线行情表 dwd_stock_daily
-- =============================================
create table if not exists dwd_stock_daily (
    trade_date date not null,
    symbol varchar(16) not null,
    open numeric(18,4),
    high numeric(18,4),
    low numeric(18,4),
    close numeric(18,4),
    pre_close numeric(18,4),
    change_amount numeric(18,4),
    change_pct numeric(10,4),
    volume bigint,
    amount numeric(20,2),
    amplitude numeric(10,4),
    turnover_rate numeric(10,4),
    turnover_rate_f numeric(10,4),
    volume_ratio numeric(10,4),
    market_value numeric(20,2),
    circulating_market_value numeric(20,2),
    pe_ttm numeric(18,4),
    pb numeric(18,4),
    ps_ttm numeric(18,4),
    suspended_flag boolean not null default false,
    is_limit_up boolean not null default false,
    is_limit_down boolean not null default false,
    adj_factor numeric(18,8),
    source varchar(32),
    created_at timestamp not null default now(),
    updated_at timestamp not null default now(),
    primary key (trade_date, symbol)
);

create index if not exists idx_stock_daily_symbol_trade_date
on dwd_stock_daily (symbol, trade_date desc);

create index if not exists idx_stock_daily_trade_date
on dwd_stock_daily (trade_date);

-- =============================================
-- 5. 复权因子表 dwd_stock_adjust_factor
-- =============================================
create table if not exists dwd_stock_adjust_factor (
    trade_date date not null,
    symbol varchar(16) not null,
    adj_factor numeric(18,8),
    forward_adj_close numeric(18,4),
    backward_adj_close numeric(18,4),
    cash_dividend numeric(18,4),
    stock_dividend numeric(18,4),
    rights_issue_ratio numeric(18,4),
    event_type varchar(32),
    source varchar(32),
    updated_at timestamp not null default now(),
    primary key (trade_date, symbol)
);

create index if not exists idx_adjust_factor_symbol_trade_date
on dwd_stock_adjust_factor (symbol, trade_date desc);

-- =============================================
-- 6. 财务指标表 dwd_stock_financial_indicator
-- =============================================
create table if not exists dwd_stock_financial_indicator (
    symbol varchar(16) not null,
    report_period date not null,
    report_type varchar(16) not null,
    announce_date date,
    eps numeric(18,4),
    bps numeric(18,4),
    roe numeric(10,4),
    roa numeric(10,4),
    gross_margin numeric(20,4),
    net_margin numeric(20,4),
    debt_to_asset numeric(10,4),
    current_ratio numeric(10,4),
    quick_ratio numeric(10,4),
    revenue numeric(20,4),
    net_profit numeric(20,4),
    revenue_yoy numeric(10,4),
    net_profit_yoy numeric(10,4),
    ocf numeric(20,2),
    ocf_to_revenue numeric(10,4),
    total_share numeric(20,4),
    liqa_share numeric(20,4),
    source varchar(32),
    updated_at timestamp not null default now(),
    primary key (symbol, report_period, report_type)
);

create index if not exists idx_financial_indicator_report_period
on dwd_stock_financial_indicator (report_period desc);

create index if not exists idx_financial_indicator_announce_date
on dwd_stock_financial_indicator (announce_date desc);

-- =============================================
-- 7. 日度技术因子表 dwd_stock_factor_daily
-- =============================================
create table if not exists dwd_stock_factor_daily (
    trade_date date not null,
    symbol varchar(16) not null,
    ma5 numeric(18,4),
    ma10 numeric(18,4),
    ma20 numeric(18,4),
    ma60 numeric(18,4),
    ma120 numeric(18,4),
    ma250 numeric(18,4),
    high_20 numeric(18,4),
    high_60 numeric(18,4),
    low_20 numeric(18,4),
    low_60 numeric(18,4),
    pct_5d numeric(10,4),
    pct_10d numeric(10,4),
    pct_20d numeric(10,4),
    pct_60d numeric(10,4),
    volume_ma5 numeric(20,2),
    volume_ma10 numeric(20,2),
    rsi_6 numeric(10,4),
    rsi_14 numeric(10,4),
    atr_14 numeric(18,4),
    macd_dif numeric(18,4),
    macd_dea numeric(18,4),
    macd_hist numeric(18,4),
    is_new_high_60d boolean,
    is_break_ma20 boolean,
    trend_score numeric(10,4),
    updated_at timestamp not null default now(),
    primary key (trade_date, symbol)
);

create index if not exists idx_factor_daily_symbol_trade_date
on dwd_stock_factor_daily (symbol, trade_date desc);

-- =============================================
-- 8. 板块主表 dwd_board_master
-- =============================================
create table if not exists dwd_board_master (
    board_code varchar(32) primary key,
    board_name varchar(128) not null,
    board_type varchar(32),
    parent_board_code varchar(32),
    is_active boolean default true,
    source varchar(32),
    updated_at timestamp not null default now()
);

-- =============================================
-- 9. 股票板块关系表 dwd_board_relation
-- =============================================
create table if not exists dwd_board_relation (
    symbol varchar(16) not null,
    board_code varchar(32) not null,
    board_type varchar(32),
    relation_source varchar(32),
    updated_at timestamp not null default now(),
    primary key (symbol, board_code)
);

create index if not exists idx_board_relation_symbol
on dwd_board_relation (symbol);

create index if not exists idx_board_relation_board_code
on dwd_board_relation (board_code);

-- 唯一索引：(symbol, board_code) 去重
create unique index if not exists idx_board_relation_symbol_board
on dwd_board_relation (symbol, board_code);

-- =============================================
-- 10. 选股宽表 mart_stock_selection_daily
-- =============================================
create table if not exists mart_stock_selection_daily (
    trade_date date not null,
    symbol varchar(16) not null,
    name varchar(64),
    exchange varchar(8),
    security_type varchar(32),
    is_st boolean,
    close_price numeric(18,4),
    change_pct numeric(10,4),
    volume_ratio numeric(10,4),
    turnover_rate_f numeric(10,4),
    amplitude numeric(10,4),
    market_value numeric(20,2),
    circulating_market_value numeric(20,2),
    pe_ttm numeric(18,4),
    pb numeric(18,4),
    ps_ttm numeric(18,4),
    ma5 numeric(18,4),
    ma10 numeric(18,4),
    ma20 numeric(18,4),
    ma60 numeric(18,4),
    rsi_14 numeric(10,4),
    macd_dif numeric(18,4),
    macd_dea numeric(18,4),
    macd_hist numeric(18,4),
    is_new_high_60d boolean,
    is_break_ma20 boolean,
    trend_score numeric(10,4),
    roe numeric(10,4),
    roa numeric(10,4),
    gross_margin numeric(10,4),
    net_margin numeric(10,4),
    debt_to_asset numeric(10,4),
    revenue_yoy numeric(10,4),
    net_profit_yoy numeric(10,4),
    board_codes varchar(512),
    board_names varchar(512),
    industry_l1 varchar(64),
    industry_l2 varchar(64),
    area varchar(64),
    is_limit_up boolean,
    is_limit_down boolean,
    suspended_flag boolean,
    composite_score numeric(10,4),
    rank_pct numeric(10,4),
    updated_at timestamp not null default now(),
    primary key (trade_date, symbol)
);

create index if not exists idx_selection_symbol
on mart_stock_selection_daily (symbol);

create index if not exists idx_selection_trade_date
on mart_stock_selection_daily (trade_date);

-- =============================================
-- 11. 用户自选股表 mart_user_watchlist
-- =============================================
create table if not exists mart_user_watchlist (
    id bigserial primary key,
    user_id varchar(64) not null,
    symbol varchar(16) not null,
    added_at timestamp not null default now()
);

create unique index if not exists uk_user_watchlist_user_symbol
on mart_user_watchlist (user_id, symbol);

create index if not exists idx_user_watchlist_user_id
on mart_user_watchlist (user_id);

-- =============================================
-- 12. ETL 任务运行表 etl_job_run
-- =============================================
create table if not exists etl_job_run (
    id bigserial primary key,
    job_name varchar(64) not null,
    biz_date date not null,
    status varchar(16) not null,
    start_time timestamp not null,
    end_time timestamp,
    duration_ms bigint,
    rows_raw int,
    rows_written int,
    error_message text,
    created_at timestamp not null default now()
);

create index if not exists idx_etl_job_run_job_biz_date
on etl_job_run (job_name, biz_date);

create index if not exists idx_etl_job_run_status
on etl_job_run (status);

-- =============================================
-- 13. ETL 检查点表 etl_checkpoint
-- =============================================
create table if not exists etl_checkpoint (
    job_name varchar(64) not null,
    checkpoint_key varchar(64) not null,
    checkpoint_value varchar(128),
    updated_at timestamp not null default now(),
    primary key (job_name, checkpoint_key)
);

-- =============================================
-- 14. 数据覆盖范围表 etl_data_coverage
-- =============================================
create table if not exists etl_data_coverage (
    symbol varchar(16) not null,
    data_type varchar(32) not null,
    start_date date,
    end_date date,
    is_full_history boolean not null default false,
    last_sync_at timestamp,
    updated_at timestamp not null default now(),
    primary key (symbol, data_type)
);

-- =============================================
-- 15. ETL 补历史任务表 etl_backfill_task
-- =============================================
create table if not exists etl_backfill_task (
    id bigserial primary key,
    symbol varchar(16) not null,
    data_type varchar(32) not null,
    start_date date,
    end_date date,
    status varchar(16) not null default 'PENDING',
    progress int default 0,
    rows_written int,
    error_message text,
    force boolean default false,
    created_at timestamp not null default now(),
    updated_at timestamp not null default now()
);

create index if not exists idx_backfill_task_symbol
on etl_backfill_task (symbol);

create index if not exists idx_backfill_task_status
on etl_backfill_task (status);

create index if not exists idx_backfill_task_created_at
on etl_backfill_task (created_at desc);

-- =============================================
-- 16. ETL 任务日志表 etl_job_run_log
-- =============================================
create table if not exists etl_job_run_log (
    id bigserial primary key,
    job_id int not null,
    level varchar(16) not null default 'INFO',
    message text not null,
    created_at timestamp not null default now()
);

create index if not exists idx_job_run_log_job_id
on etl_job_run_log (job_id);

create index if not exists idx_job_run_log_created_at
on etl_job_run_log (created_at);
