#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技术因子计算脚本
================
基于 dwd_stock_daily 计算技术指标，写入 dwd_stock_factor_daily

因子列表:
- MA均线: ma5, ma10, ma20, ma60, ma120, ma250
- 高低价: high_20, high_60, low_20, low_60
- 涨跌幅: pct_5d, pct_10d, pct_20d, pct_60d
- 成交量均线: volume_ma5, volume_ma10
- RSI: rsi_6, rsi_14
- ATR: atr_14
- MACD: macd_dif, macd_dea, macd_hist
- 标记: is_new_high_60d, is_break_ma20
- 趋势评分: trend_score

用法:
    # 计算指定日期
    python compute_factor.py --date 2026-04-29

    # 计算日期范围
    python compute_factor.py --start-date 2026-01-01 --end-date 2026-04-29

    # 全量重算
    python compute_factor.py --full
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
LOG_FILE = os.path.join(LOG_DIR, f'compute_factor_{datetime.now().strftime("%Y%m%d")}.log')


def setup_logging():
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


def calculate_factors_for_symbol(conn, symbol: str, dates: list) -> pd.DataFrame:
    """
    计算单只股票的技术因子

    Args:
        conn: 数据库连接
        symbol: 股票代码
        dates: 需要计算的日期列表

    Returns:
        DataFrame with all factors
    """
    if not dates:
        return pd.DataFrame()

    # 获取历史数据（需要足够长的历史计算均线）
    start_date = min(dates)
    end_date = max(dates)
    # 往前多取250天用于计算MA250
    lookback_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=300)).strftime('%Y-%m-%d')

    query = """
        SELECT trade_date, symbol, open, high, low, close, volume, amount,
               turnover_rate, turnover_rate_f, change_pct, amplitude
        FROM dwd_stock_daily
        WHERE symbol = %s
          AND trade_date >= %s
          AND trade_date <= %s
        ORDER BY trade_date
    """

    df = pd.read_sql(query, conn, params=(symbol, lookback_start, end_date))

    if df.empty:
        return pd.DataFrame()

    df['trade_date'] = pd.to_datetime(df['trade_date'])

    # ========== 计算各项因子 ==========

    # 1. MA 均线
    for n in [5, 10, 20, 60, 120, 250]:
        df[f'ma{n}'] = df['close'].rolling(window=n, min_periods=1).mean()

    # 2. N日高低价
    for n in [20, 60]:
        df[f'high_{n}'] = df['high'].rolling(window=n, min_periods=1).max()
        df[f'low_{n}'] = df['low'].rolling(window=n, min_periods=1).min()

    # 3. N日涨跌幅
    for n in [5, 10, 20, 60]:
        df[f'pct_{n}d'] = df['close'].pct_change(periods=n) * 100

    # 4. 成交量均线
    for n in [5, 10]:
        df[f'volume_ma{n}'] = df['volume'].rolling(window=n, min_periods=1).mean()

    # 5. RSI
    for period in [6, 14]:
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
        rs = gain / loss
        df[f'rsi_{period}'] = (100 - (100 / (1 + rs))).fillna(50)

    # 6. ATR (Average True Range)
    high = df['high']
    low = df['low']
    prev_close = df['close'].shift(1)
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(window=14, min_periods=1).mean()

    # 7. MACD (12, 26, 9)
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    macd_dif = ema12 - ema26
    macd_dea = macd_dif.ewm(span=9, adjust=False).mean()
    df['macd_dif'] = macd_dif
    df['macd_dea'] = macd_dea
    df['macd_hist'] = 2 * (macd_dif - macd_dea)

    # 8. is_new_high_60d
    df['is_new_high_60d'] = df['close'] >= df['high_60']

    # 9. is_break_ma20 (当天收盘价上穿MA20)
    prev_close_price = df['close'].shift(1)
    prev_ma20 = df['ma20'].shift(1)
    df['is_break_ma20'] = (df['close'] > df['ma20']) & (prev_close_price <= prev_ma20)

    # 10. trend_score (趋势评分)
    df['trend_score'] = calculate_trend_score(df)

    # 只返回目标日期范围的数据
    target_start = datetime.strptime(start_date, '%Y-%m-%d')
    target_end = datetime.strptime(end_date, '%Y-%m-%d')
    result_df = df[(df['trade_date'] >= target_start) & (df['trade_date'] <= target_end)].copy()

    return result_df


def calculate_trend_score(df: pd.DataFrame) -> pd.Series:
    """
    计算趋势评分 (0-100)

    评分维度:
    - 均线多头排列 (25%): MA5>MA10>MA20>MA60
    - 趋势强度 (25%): (close - MA60) / MA60 * 100，标准化到0-100
    - 动量 (25%): 近20日涨跌幅 pct_20d，标准化到0-100
    - 波动率 (25%): ATR/close * 100，越低分越高

    各维度先标准化到 0-100，再加权平均
    """
    scores = pd.DataFrame(index=df.index)

    # ========== 1. 均线多头排列 (0-100) ==========
    ma排列 = (
        (df['ma5'] > df['ma10']).astype(int) +
        (df['ma10'] > df['ma20']).astype(int) +
        (df['ma20'] > df['ma60']).astype(int) +
        (df['close'] > df['ma5']).astype(int)
    )
    # 4项全中=100, 3项=75, 2项=50, 1项=25, 0项=0
    scores['ma_score'] = ma排列 * 25

    # ========== 2. 趋势强度 (0-100) ==========
    # (close - MA60) / MA60 * 100，反映价格相对长期均线的位置
    trend_pct = (df['close'] - df['ma60']) / df['ma60'] * 100
    # 标准化: 假设 -20% ~ +50% 区间映射到 0-100
    trend_pct_clipped = trend_pct.clip(-20, 50)
    scores['trend_score_raw'] = (trend_pct_clipped + 20) / 70 * 100

    # ========== 3. 动量 (0-100) ==========
    # 近20日涨跌幅 pct_20d，标准化
    momentum = df['pct_20d'].fillna(0)
    momentum_clipped = momentum.clip(-30, 80)
    scores['momentum_score'] = (momentum_clipped + 30) / 110 * 100

    # ========== 4. 波动率 (0-100) ==========
    # ATR/close * 100，越低表示越稳健，给高分
    volatility = (df['atr_14'] / df['close'] * 100).fillna(0)
    # 假设 0% ~ 10% 区间映射到 100-0 (越低越高分)
    volatility_clipped = volatility.clip(0, 10)
    scores['volatility_score'] = (10 - volatility_clipped) / 10 * 100

    # ========== 加权平均 ==========
    final_score = (
        scores['ma_score'] * 0.25 +
        scores['trend_score_raw'] * 0.25 +
        scores['momentum_score'] * 0.25 +
        scores['volatility_score'] * 0.25
    )

    # 限制在 0-100 范围
    return final_score.clip(0, 100).round(2)


def upsert_factors(conn, df: pd.DataFrame, trade_date: str) -> int:
    """
    批量写入技术因子数据 (幂等 upsert)
    """
    if df.empty:
        return 0

    records = []
    for _, row in df.iterrows():
        records.append({
            'trade_date': trade_date,
            'symbol': row['symbol'],
            'ma5': round(row['ma5'], 4) if pd.notna(row['ma5']) else None,
            'ma10': round(row['ma10'], 4) if pd.notna(row['ma10']) else None,
            'ma20': round(row['ma20'], 4) if pd.notna(row['ma20']) else None,
            'ma60': round(row['ma60'], 4) if pd.notna(row['ma60']) else None,
            'ma120': round(row['ma120'], 4) if pd.notna(row['ma120']) else None,
            'ma250': round(row['ma250'], 4) if pd.notna(row['ma250']) else None,
            'high_20': round(row['high_20'], 4) if pd.notna(row['high_20']) else None,
            'high_60': round(row['high_60'], 4) if pd.notna(row['high_60']) else None,
            'low_20': round(row['low_20'], 4) if pd.notna(row['low_20']) else None,
            'low_60': round(row['low_60'], 4) if pd.notna(row['low_60']) else None,
            'pct_5d': round(row['pct_5d'], 4) if pd.notna(row['pct_5d']) else None,
            'pct_10d': round(row['pct_10d'], 4) if pd.notna(row['pct_10d']) else None,
            'pct_20d': round(row['pct_20d'], 4) if pd.notna(row['pct_20d']) else None,
            'pct_60d': round(row['pct_60d'], 4) if pd.notna(row['pct_60d']) else None,
            'volume_ma5': round(row['volume_ma5'], 2) if pd.notna(row['volume_ma5']) else None,
            'volume_ma10': round(row['volume_ma10'], 2) if pd.notna(row['volume_ma10']) else None,
            'rsi_6': round(row['rsi_6'], 4) if pd.notna(row['rsi_6']) else None,
            'rsi_14': round(row['rsi_14'], 4) if pd.notna(row['rsi_14']) else None,
            'atr_14': round(row['atr_14'], 4) if pd.notna(row['atr_14']) else None,
            'macd_dif': round(row['macd_dif'], 4) if pd.notna(row['macd_dif']) else None,
            'macd_dea': round(row['macd_dea'], 4) if pd.notna(row['macd_dea']) else None,
            'macd_hist': round(row['macd_hist'], 4) if pd.notna(row['macd_hist']) else None,
            'is_new_high_60d': bool(row['is_new_high_60d']) if pd.notna(row['is_new_high_60d']) else False,
            'is_break_ma20': bool(row['is_break_ma20']) if pd.notna(row['is_break_ma20']) else False,
            'trend_score': round(row['trend_score'], 4) if pd.notna(row['trend_score']) else None,
            'updated_at': datetime.now(),
        })

    cursor = conn.cursor()
    sql = """
        INSERT INTO dwd_stock_factor_daily (
            trade_date, symbol, ma5, ma10, ma20, ma60, ma120, ma250,
            high_20, high_60, low_20, low_60,
            pct_5d, pct_10d, pct_20d, pct_60d,
            volume_ma5, volume_ma10,
            rsi_6, rsi_14, atr_14,
            macd_dif, macd_dea, macd_hist,
            is_new_high_60d, is_break_ma20, trend_score, updated_at
        ) VALUES (
            %(trade_date)s, %(symbol)s, %(ma5)s, %(ma10)s, %(ma20)s, %(ma60)s, %(ma120)s, %(ma250)s,
            %(high_20)s, %(high_60)s, %(low_20)s, %(low_60)s,
            %(pct_5d)s, %(pct_10d)s, %(pct_20d)s, %(pct_60d)s,
            %(volume_ma5)s, %(volume_ma10)s,
            %(rsi_6)s, %(rsi_14)s, %(atr_14)s,
            %(macd_dif)s, %(macd_dea)s, %(macd_hist)s,
            %(is_new_high_60d)s, %(is_break_ma20)s, %(trend_score)s, %(updated_at)s
        )
        ON CONFLICT (trade_date, symbol) DO UPDATE SET
            ma5 = EXCLUDED.ma5, ma10 = EXCLUDED.ma10, ma20 = EXCLUDED.ma20,
            ma60 = EXCLUDED.ma60, ma120 = EXCLUDED.ma120, ma250 = EXCLUDED.ma250,
            high_20 = EXCLUDED.high_20, high_60 = EXCLUDED.high_60,
            low_20 = EXCLUDED.low_20, low_60 = EXCLUDED.low_60,
            pct_5d = EXCLUDED.pct_5d, pct_10d = EXCLUDED.pct_10d,
            pct_20d = EXCLUDED.pct_20d, pct_60d = EXCLUDED.pct_60d,
            volume_ma5 = EXCLUDED.volume_ma5, volume_ma10 = EXCLUDED.volume_ma10,
            rsi_6 = EXCLUDED.rsi_6, rsi_14 = EXCLUDED.rsi_14, atr_14 = EXCLUDED.atr_14,
            macd_dif = EXCLUDED.macd_dif, macd_dea = EXCLUDED.macd_dea, macd_hist = EXCLUDED.macd_hist,
            is_new_high_60d = EXCLUDED.is_new_high_60d, is_break_ma20 = EXCLUDED.is_break_ma20,
            trend_score = EXCLUDED.trend_score, updated_at = EXCLUDED.updated_at
    """
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


def get_all_symbols(conn) -> list:
    """获取所有股票代码"""
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM dwd_security_master WHERE status = 'LISTED' ORDER BY symbol")
    symbols = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return symbols


def main():
    logger = setup_logging()

    parser = argparse.ArgumentParser(description='技术因子计算脚本')
    parser.add_argument('--date', type=str, help='指定单个日期 YYYY-MM-DD')
    parser.add_argument('--start-date', type=str, help='起始日期 YYYY-MM-DD')
    parser.add_argument('--end-date', type=str, help='结束日期 YYYY-MM-DD')
    parser.add_argument('--full', action='store_true', help='全量重算')
    args = parser.parse_args()

    # 确定日期范围
    if args.full:
        # 全量重算：取最近2年
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
        # 默认计算最近5个交易日
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

    logger.info(f"待计算交易日数: {len(trade_dates)}")

    # 获取股票列表
    symbols = get_all_symbols(conn)
    total_stocks = len(symbols)
    logger.info(f"待计算股票数: {total_stocks}")

    total_records = 0
    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("技术因子计算开始")
    logger.info("=" * 60)

    for idx, symbol in enumerate(symbols):
        try:
            df = calculate_factors_for_symbol(conn, symbol, trade_dates)
            if not df.empty:
                for td in trade_dates:
                    day_df = df[df['trade_date'] == pd.to_datetime(td)]
                    if not day_df.empty:
                        written = upsert_factors(conn, day_df, td)
                        total_records += written

            if (idx + 1) % 500 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = (idx + 1) / elapsed
                logger.info(f"进度: {idx+1}/{total_stocks} ({rate:.1f}只/秒)")

        except Exception as e:
            logger.warning(f"处理 {symbol} 时出错: {e}")

    elapsed = (datetime.now() - start_time).total_seconds()
    conn.close()

    logger.info("=" * 60)
    logger.info(f"✅ 技术因子计算完成!")
    logger.info(f"总耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
    logger.info(f"处理股票: {total_stocks} 只")
    logger.info(f"写入记录: {total_records} 条")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
