#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
选股宽表构建脚本
================
将多表数据聚合生成 mart_stock_selection_daily

数据来源:
- dwd_security_master: 股票基础信息
- dwd_stock_daily: 当日行情
- dwd_stock_factor_daily: 技术因子
- dwd_stock_financial_indicator: 财务指标（取最新报告期）
- dwd_board_relation: 板块关系

输出:
- mart_stock_selection_daily

composite_score 计算:
    30% * trend_score
  + 20% * roe (标准化)
  + 15% * revenue_yoy (标准化)
  + 15% * net_profit_yoy (标准化)
  + 10% * volume_ratio (标准化)
  + 10% * change_pct (标准化)

用法:
    # 构建指定日期
    python build_selection_mart.py --date 2026-04-29

    # 构建日期范围
    python build_selection_mart.py --start-date 2026-01-01 --end-date 2026-04-29

    # 全量重算
    python build_selection_mart.py --full
"""

import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
import argparse

# ========== 配置 ==========
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '192.168.3.16'),
    'port': int(os.environ.get('DB_PORT', '5432')),
    'database': os.environ.get('DB_NAME', 'stock_cache_system'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', '')
}

LOG_DIR = os.environ.get("SYNC_LOG_DIR", "/app/logs")
LOG_FILE = os.path.join(LOG_DIR, f'build_selection_mart_{datetime.now().strftime("%Y%m%d")}.log')

# ========== 评分常量 ==========
# 标准化范围 (min, max) - 用于 normalize_score
SCORE_RANGE_ROE = (-50, 50)           # ROE: -50% ~ 50%
SCORE_RANGE_REVENUE_YOY = (-100, 500) # 营收增速: -100% ~ 500%
SCORE_RANGE_NET_PROFIT_YOY = (-200, 500)  # 净利润增速: -200% ~ 500%
SCORE_RANGE_VOLUME_RATIO = (0, 10)    # 量比: 0 ~ 10
SCORE_RANGE_CHANGE_PCT = (-10, 10)    # 涨跌幅: -10% ~ 10%

# 复合评分权重
WEIGHT_TREND = 0.30
WEIGHT_ROE = 0.20
WEIGHT_REVENUE_YOY = 0.15
WEIGHT_NET_PROFIT_YOY = 0.15
WEIGHT_VOLUME_RATIO = 0.10
WEIGHT_CHANGE_PCT = 0.10


def setup_logging():
    global logger
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        logger.addHandler(fh)
        logger.addHandler(sh)
    return logger


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def normalize_score(series: pd.Series, min_val=None, max_val=None) -> pd.Series:
    """
    将数值标准化到 0-100 范围
    使用 min-max 标准化
    """
    if series.isna().all():
        return series.fillna(50)  # 全空则返回50

    s = series.copy()
    if min_val is not None:
        s = s.clip(lower=min_val)
    if max_val is not None:
        s = s.clip(upper=max_val)

    min_val_actual = s.min()
    max_val_actual = s.max()

    if max_val_actual == min_val_actual:
        return pd.Series(50, index=s.index)

    return ((s - min_val_actual) / (max_val_actual - min_val_actual) * 100).fillna(50)


def calculate_composite_score(df: pd.DataFrame) -> pd.Series:
    """
    计算综合评分 (0-100)

    权重:
    - trend_score: 30%
    - roe: 20%
    - revenue_yoy: 15%
    - net_profit_yoy: 15%
    - volume_ratio: 10%
    - change_pct: 10%
    """
    # 标准化各项指标
    scores = pd.DataFrame(index=df.index)

    # trend_score 已经是 0-100，直接使用
    scores['trend'] = df['trend_score'].fillna(50)

    # roe 标准化
    scores['roe'] = normalize_score(df['roe'], *SCORE_RANGE_ROE)

    # revenue_yoy 标准化
    scores['revenue_yoy'] = normalize_score(df['revenue_yoy'], *SCORE_RANGE_REVENUE_YOY)

    # net_profit_yoy 标准化
    scores['net_profit_yoy'] = normalize_score(df['net_profit_yoy'], *SCORE_RANGE_NET_PROFIT_YOY)

    # volume_ratio 标准化
    scores['volume_ratio'] = normalize_score(df['volume_ratio'].fillna(1), *SCORE_RANGE_VOLUME_RATIO)

    # change_pct 标准化
    scores['change_pct'] = normalize_score(df['change_pct'], *SCORE_RANGE_CHANGE_PCT)

    # 加权平均
    composite = (
        scores['trend'] * WEIGHT_TREND +
        scores['roe'] * WEIGHT_ROE +
        scores['revenue_yoy'] * WEIGHT_REVENUE_YOY +
        scores['net_profit_yoy'] * WEIGHT_NET_PROFIT_YOY +
        scores['volume_ratio'] * WEIGHT_VOLUME_RATIO +
        scores['change_pct'] * WEIGHT_CHANGE_PCT
    )

    return composite.clip(0, 100).round(2)


def get_selection_data(conn, trade_date: str) -> pd.DataFrame:
    """
    获取选股宽表数据

    聚合: 日线 + 技术因子 + 财务指标 + 板块关系
    """
    query = """
        WITH latest_finance AS (
            -- 取每只股票最新报告期的财务数据
            SELECT DISTINCT ON (symbol)
                symbol,
                report_period,
                report_type,
                roe,
                roa,
                gross_margin,
                net_margin,
                debt_to_asset,
                revenue_yoy,
                net_profit_yoy
            FROM dwd_stock_financial_indicator
            WHERE report_period <= %s
            ORDER BY symbol, report_period DESC
        ),
        board_info AS (
            -- 取每只股票最新的板块信息（无trade_date字段，取最新记录）
            SELECT DISTINCT ON (symbol)
                symbol,
                board_code,
                board_type
            FROM dwd_board_relation
            ORDER BY symbol, updated_at DESC
        )
        SELECT
            d.symbol,
            m.name,
            m.exchange,
            m.security_type,
            m.is_st,
            d.close AS close_price,
            d.change_pct,
            d.volume_ratio,
            d.turnover_rate_f,
            d.amplitude,
            d.market_value,
            d.circulating_market_value,
            d.pe_ttm,
            d.pb,
            d.ps_ttm,
            d.is_limit_up,
            d.is_limit_down,
            d.suspended_flag,
            -- 技术因子
            f.ma5,
            f.ma10,
            f.ma20,
            f.ma60,
            f.rsi_14,
            f.macd_dif,
            f.macd_dea,
            f.macd_hist,
            f.is_new_high_60d,
            f.is_break_ma20,
            f.trend_score,
            -- 财务指标
            lf.roe,
            lf.roa,
            lf.gross_margin,
            lf.net_margin,
            lf.debt_to_asset,
            lf.revenue_yoy,
            lf.net_profit_yoy,
            -- 板块
            b.board_code,
            b.board_type,
            m.industry_l1,
            m.industry_l2,
            m.area
        FROM dwd_stock_daily d
        JOIN dwd_security_master m ON d.symbol = m.symbol
        LEFT JOIN dwd_stock_factor_daily f
            ON d.symbol = f.symbol AND d.trade_date = f.trade_date
        LEFT JOIN latest_finance lf ON d.symbol = lf.symbol
        LEFT JOIN board_info b ON d.symbol = b.symbol
        WHERE d.trade_date = %s
          AND m.status = 'LISTED'
        ORDER BY d.symbol
    """

    df = pd.read_sql(query, conn, params=(trade_date, trade_date))
    return df


def build_board_names(conn, symbols: list, trade_date: str) -> dict:
    """获取每只股票的板块名称"""
    if not symbols:
        return {}

    query = """
        WITH latest_boards AS (
            SELECT DISTINCT ON (symbol, board_code)
                symbol,
                board_code,
                board_type
            FROM dwd_board_relation
            ORDER BY symbol, board_code, updated_at DESC
        )
        SELECT lb.symbol, lb.board_code, bm.board_name
        FROM latest_boards lb
        JOIN dwd_board_master bm ON lb.board_code = bm.board_code
        WHERE lb.symbol = ANY(%s)
    """

    cursor = conn.cursor()
    cursor.execute(query, (symbols,))
    rows = cursor.fetchall()
    cursor.close()

    board_map = {}
    for sym, board_code, board_name in rows:
        if sym not in board_map:
            board_map[sym] = {'codes': [], 'names': []}
        board_map[sym]['codes'].append(board_code)
        board_map[sym]['names'].append(board_name)

    return board_map


def upsert_selection_data(conn, df: pd.DataFrame, trade_date: str) -> int:
    """
    批量写入选股宽表数据
    """
    if df.empty:
        return 0

    # 获取板块信息
    symbols = df['symbol'].tolist()
    board_info = {}
    try:
        board_info = build_board_names(conn, symbols, trade_date)
    except Exception as e:
        logger.warning(f"获取板块信息失败: {e}")

    records = []
    for _, row in df.iterrows():
        sym = row['symbol']
        boards = board_info.get(sym, {'codes': [], 'names': []})

        records.append({
            'trade_date': trade_date,
            'symbol': sym,
            'name': row['name'],
            'exchange': row['exchange'],
            'security_type': row['security_type'],
            'is_st': row['is_st'],
            'close_price': row['close_price'],
            'change_pct': row['change_pct'],
            'volume_ratio': row['volume_ratio'],
            'turnover_rate_f': row['turnover_rate_f'],
            'amplitude': row['amplitude'],
            'market_value': row['market_value'],
            'circulating_market_value': row['circulating_market_value'],
            'pe_ttm': row['pe_ttm'],
            'pb': row['pb'],
            'ps_ttm': row['ps_ttm'],
            'ma5': row['ma5'],
            'ma10': row['ma10'],
            'ma20': row['ma20'],
            'ma60': row['ma60'],
            'rsi_14': row['rsi_14'],
            'macd_dif': row['macd_dif'],
            'macd_dea': row['macd_dea'],
            'macd_hist': row['macd_hist'],
            'is_new_high_60d': row['is_new_high_60d'],
            'is_break_ma20': row['is_break_ma20'],
            'trend_score': row['trend_score'],
            'roe': row['roe'],
            'roa': row['roa'],
            'gross_margin': row['gross_margin'],
            'net_margin': row['net_margin'],
            'debt_to_asset': row['debt_to_asset'],
            'revenue_yoy': row['revenue_yoy'],
            'net_profit_yoy': row['net_profit_yoy'],
            'board_codes': ','.join(boards.get('codes', [])) if boards.get('codes') else None,
            'board_names': ','.join(boards.get('names', [])) if boards.get('names') else None,
            'industry_l1': row['industry_l1'],
            'industry_l2': row['industry_l2'],
            'area': row['area'],
            'is_limit_up': row['is_limit_up'],
            'is_limit_down': row['is_limit_down'],
            'suspended_flag': row['suspended_flag'],
            'composite_score': row['composite_score'],
            'rank_pct': row['rank_pct'],
            'updated_at': datetime.now(),
        })

    sql = """
        INSERT INTO mart_stock_selection_daily (
            trade_date, symbol, name, exchange, security_type, is_st,
            close_price, change_pct, volume_ratio, turnover_rate_f, amplitude,
            market_value, circulating_market_value, pe_ttm, pb, ps_ttm,
            ma5, ma10, ma20, ma60, rsi_14, macd_dif, macd_dea, macd_hist,
            is_new_high_60d, is_break_ma20, trend_score,
            roe, roa, gross_margin, net_margin, debt_to_asset,
            revenue_yoy, net_profit_yoy,
            board_codes, board_names, industry_l1, industry_l2, area,
            is_limit_up, is_limit_down, suspended_flag,
            composite_score, rank_pct, updated_at
        ) VALUES (
            %(trade_date)s, %(symbol)s, %(name)s, %(exchange)s, %(security_type)s, %(is_st)s,
            %(close_price)s, %(change_pct)s, %(volume_ratio)s, %(turnover_rate_f)s, %(amplitude)s,
            %(market_value)s, %(circulating_market_value)s, %(pe_ttm)s, %(pb)s, %(ps_ttm)s,
            %(ma5)s, %(ma10)s, %(ma20)s, %(ma60)s, %(rsi_14)s, %(macd_dif)s, %(macd_dea)s, %(macd_hist)s,
            %(is_new_high_60d)s, %(is_break_ma20)s, %(trend_score)s,
            %(roe)s, %(roa)s, %(gross_margin)s, %(net_margin)s, %(debt_to_asset)s,
            %(revenue_yoy)s, %(net_profit_yoy)s,
            %(board_codes)s, %(board_names)s, %(industry_l1)s, %(industry_l2)s, %(area)s,
            %(is_limit_up)s, %(is_limit_down)s, %(suspended_flag)s,
            %(composite_score)s, %(rank_pct)s, %(updated_at)s
        )
        ON CONFLICT (trade_date, symbol) DO UPDATE SET
            name = EXCLUDED.name,
            close_price = EXCLUDED.close_price,
            change_pct = EXCLUDED.change_pct,
            volume_ratio = EXCLUDED.volume_ratio,
            turnover_rate_f = EXCLUDED.turnover_rate_f,
            amplitude = EXCLUDED.amplitude,
            market_value = EXCLUDED.market_value,
            pe_ttm = EXCLUDED.pe_ttm,
            pb = EXCLUDED.pb,
            trend_score = EXCLUDED.trend_score,
            roe = EXCLUDED.roe,
            revenue_yoy = EXCLUDED.revenue_yoy,
            net_profit_yoy = EXCLUDED.net_profit_yoy,
            composite_score = EXCLUDED.composite_score,
            rank_pct = EXCLUDED.rank_pct,
            updated_at = EXCLUDED.updated_at
    """

    cursor = conn.cursor()
    cursor.executemany(sql, records)
    conn.commit()
    cursor.close()

    return len(records)


def get_trade_dates(conn, start_date: str, end_date: str) -> list:
    """获取指定范围内的交易日列表"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT trade_date FROM dwd_trade_calendar
        WHERE trade_date >= %s AND trade_date <= %s AND is_open = true
        ORDER BY trade_date
    """, (start_date, end_date))
    dates = [row[0].strftime('%Y-%m-%d') for row in cursor.fetchall()]
    cursor.close()
    return dates


def main():
    logger = setup_logging()

    parser = argparse.ArgumentParser(description='选股宽表构建脚本')
    parser.add_argument('--date', type=str, help='指定单个日期 YYYY-MM-DD')
    parser.add_argument('--start-date', type=str, help='起始日期 YYYY-MM-DD')
    parser.add_argument('--end-date', type=str, help='结束日期 YYYY-MM-DD')
    parser.add_argument('--full', action='store_true', help='全量重算')
    args = parser.parse_args()

    # 确定日期范围
    if args.full:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
        logger.info(f"全量重算模式: {start_date} ~ {end_date}")
    elif args.date:
        start_date = args.date
        end_date = args.date
        logger.info(f"单日模式: {start_date}")
    elif args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
        logger.info(f"日期范围模式: {start_date} ~ {end_date}")
    else:
        # 默认最近5个交易日
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        logger.info(f"默认模式 (最近交易日): {start_date} ~ {end_date}")

    conn = get_db_connection()

    # 获取交易日列表
    trade_dates = get_trade_dates(conn, start_date, end_date)
    if not trade_dates:
        logger.warning("指定范围内没有交易日")
        conn.close()
        return

    logger.info(f"待构建交易日数: {len(trade_dates)}")

    total_records = 0
    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("选股宽表构建开始")
    logger.info("=" * 60)

    for idx, trade_date in enumerate(trade_dates):
        try:
            # 获取数据
            df = get_selection_data(conn, trade_date)
            if df.empty:
                logger.info(f"  {trade_date}: 无数据")
                continue

            # 计算综合评分
            df['composite_score'] = calculate_composite_score(df)

            # 计算排名百分位
            df['rank_pct'] = df['composite_score'].rank(pct=True) * 100

            # 写入
            written = upsert_selection_data(conn, df, trade_date)
            total_records += written

            logger.info(f"  {trade_date}: 写入 {written} 条")

            if (idx + 1) % 10 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = (idx + 1) / elapsed
                logger.info(f"进度: {idx+1}/{len(trade_dates)} ({rate:.1f}天/秒)")

        except Exception as e:
            logger.error(f"处理 {trade_date} 时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())

    elapsed = (datetime.now() - start_time).total_seconds()
    conn.close()

    logger.info("=" * 60)
    logger.info(f"✅ 选股宽表构建完成!")
    logger.info(f"总耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
    logger.info(f"处理交易日: {len(trade_dates)} 天")
    logger.info(f"写入记录: {total_records} 条")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
