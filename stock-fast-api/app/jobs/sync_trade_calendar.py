#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ETL Script: 从 Baostock 同步 dwd_trade_calendar 交易日历

数据来源:
- query_trade_dates: 获取指定日期区间的交易日历 (calendar_date, is_trading_day)

目标表: dwd_trade_calendar
主键: (exchange, trade_date)

说明:
- A股三大交易所(Shanghai/SZ/BJ)使用同一套日历，同一天要么都开要么都休
- 因此 Baostock 返回的 is_trading_day 同时适用于 SH/SZ/BJ
- prev_trade_date / next_trade_date 由本地计算得出
- 每次同步会覆盖指定区间，保证历史数据一致性

用法:
    # 同步2026年全年日历
    python sync_trade_calendar.py --start-date 2026-01-01 --end-date 2026-12-31

    # 同步未来一年（默认）
    python sync_trade_calendar.py
"""
import baostock as bs
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
import os
import sys
import logging
import argparse


# ========== 配置 ==========
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '192.168.3.16'),
    'port': int(os.environ.get('DB_PORT', '5432')),
    'database': os.environ.get('DB_NAME', 'stock_cache_system'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', ''),
}

LOG_DIR = os.environ.get('SYNC_LOG_DIR', '/app/logs')
BATCH_SIZE = 500


# ========== 日志 ==========
def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(
        LOG_DIR,
        f"sync_trade_calendar_{datetime.now().strftime('%Y%m%d')}.log"
    )
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger('sync_trade_calendar')


# ========== 核心逻辑 ==========

def sync_trade_calendar(start_date: str | None = None, end_date: str | None = None) -> int:
    """
    从 Baostock 同步交易日历到 dwd_trade_calendar。

    Returns: 写入的记录数
    """
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info(f"【交易日历同步】开始 | start={start_date} end={end_date}")

    # 1. 确定同步区间
    today = datetime.now()
    if not end_date:
        end_date = (today + timedelta(days=365)).strftime('%Y-%m-%d')
    if not start_date:
        start_date = today.strftime('%Y-01-01')

    logger.info(f"同步区间: {start_date} ~ {end_date}")

    # 2. 从 Baostock 获取日历数据
    bs.login()
    try:
        rs = bs.query_trade_dates(start_date=start_date, end_date=end_date)
        rows = []
        while rs.error_code == '0' and rs.next():
            rows.append(rs.get_row_data())
        if not rows:
            logger.warning("Baostock 未返回任何交易日历数据")
            return 0
        logger.info(f"Baostock 返回 {len(rows)} 条记录")
    finally:
        bs.logout()

    # 3. 构建记录列表 (三大交易所共用同一日历)
    all_records = []
    trade_days = []

    for row in rows:
        cal_date_str = row[0]       # calendar_date
        is_open = row[1] == '1'     # is_trading_day
        cal_date = datetime.strptime(cal_date_str, '%Y-%m-%d').date()

        if is_open:
            trade_days.append(cal_date)

        for exchange in ['SH', 'SZ', 'BJ']:
            all_records.append({
                'exchange': exchange,
                'trade_date': cal_date,
                'is_open': is_open,
            })

    # 4. 计算 prev_trade_date / next_trade_date
    trade_days.sort()

    for rec in all_records:
        d = rec['trade_date']
        prev_days = [td for td in trade_days if td < d]
        rec['prev_trade_date'] = prev_days[-1] if prev_days else None
        next_days = [td for td in trade_days if td > d]
        rec['next_trade_date'] = next_days[0] if next_days else None
        rec['week_no'] = d.isocalendar()[1]
        rec['month_no'] = d.month
        rec['quarter_no'] = (d.month - 1) // 3 + 1
        rec['year_no'] = d.year

    logger.info(f"构建完成，共 {len(all_records)} 条记录（含 SH/SZ/BJ 三份）")

    # 5. 写入数据库 (upsert)
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn:
            with conn.cursor() as cur:
                for exchange in ['SH', 'SZ', 'BJ']:
                    cur.execute(
                        """
                        DELETE FROM dwd_trade_calendar
                        WHERE exchange = %s
                          AND trade_date >= %s
                          AND trade_date <= %s
                        """,
                        (exchange, start_date, end_date)
                    )
                    logger.info(f"  [{exchange}] 已删除 [{start_date} ~ {end_date}] 区间旧数据")

        with conn:
            with conn.cursor() as cur:
                values = [
                    (
                        r['exchange'],
                        r['trade_date'],
                        r['is_open'],
                        r.get('prev_trade_date'),
                        r.get('next_trade_date'),
                        r.get('week_no'),
                        r.get('month_no'),
                        r.get('quarter_no'),
                        r.get('year_no'),
                        datetime.now(),
                    )
                    for r in all_records
                ]

                execute_values(
                    cur,
                    """
                    INSERT INTO dwd_trade_calendar
                        (exchange, trade_date, is_open, prev_trade_date, next_trade_date,
                         week_no, month_no, quarter_no, year_no, updated_at)
                    VALUES %s
                    ON CONFLICT (exchange, trade_date) DO UPDATE SET
                        is_open = EXCLUDED.is_open,
                        prev_trade_date = EXCLUDED.prev_trade_date,
                        next_trade_date = EXCLUDED.next_trade_date,
                        week_no = EXCLUDED.week_no,
                        month_no = EXCLUDED.month_no,
                        quarter_no = EXCLUDED.quarter_no,
                        year_no = EXCLUDED.year_no,
                        updated_at = EXCLUDED.updated_at
                    """,
                    values,
                    page_size=BATCH_SIZE,
                )

        logger.info(f"【交易日历同步】完成，写入 {len(all_records)} 条记录")
        return len(all_records)

    finally:
        conn.close()


# ========== CLI 入口 ==========
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='交易日历同步脚本')
    parser.add_argument('--start-date', help='开始日期 YYYY-MM-DD')
    parser.add_argument('--end-date', help='结束日期 YYYY-MM-DD')
    args = parser.parse_args()

    try:
        count = sync_trade_calendar(
            start_date=args.start_date,
            end_date=args.end_date,
        )
        print(f"\n完成，共写入 {count} 条记录")
    except Exception as e:
        print(f"\n失败: {e}")
        sys.exit(1)
