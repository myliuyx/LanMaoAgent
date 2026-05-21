#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ETL Script: 从 Baostock 同步 dwd_board_master 板块主数据

数据来源:
- query_stock_industry: 查询每只股票的行业分类
- 全量股票从 dwd_security_master 读取

目标表: dwd_board_master
主键: board_code

板块类型:
- INDUSTRY: 证监会行业分类（Baostock 可获取）

用法:
    python sync_board.py
"""
import baostock as bs
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import re
import os
import sys
import logging
import argparse
import signal


# ========== 配置 ==========
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '192.168.3.16'),
    'port': int(os.environ.get('DB_PORT', '5432')),
    'database': os.environ.get('DB_NAME', 'stock_cache_system'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', ''),
}

MAX_WORKERS = int(os.environ.get('SYNC_WORKERS', '10'))
RATE_LIMIT_DELAY = float(os.environ.get('SYNC_RATE_DELAY', '0.02'))
BATCH_SIZE = 200
LOG_DIR = os.environ.get('SYNC_LOG_DIR', '/app/logs')
QUERY_TIMEOUT = float(os.environ.get('SYNC_QUERY_TIMEOUT', '10'))  # 单次查询超时(秒)


# ========== 日志 ==========
def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"sync_board_{datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger('sync_board')


def to_baostock_code(symbol: str) -> str:
    """standard symbol -> baostock code, e.g. 600519.SH -> sh.600519"""
    ticker, exchange = symbol.split('.')
    if exchange == 'SH':
        return f'sh.{ticker}'
    elif exchange == 'SZ':
        return f'sz.{ticker}'
    elif exchange == 'BJ':
        return f'bj.{ticker}'
    return f'sh.{ticker}'


def parse_industry(raw: str) -> tuple:
    """
    从 'C15酒、饮料和精制茶制造业' 提取 board_code 和 board_name
    返回 (board_code, board_name) 或 (None, None)
    """
    if not raw:
        return None, None
    m = re.match(r'^([A-Z]\d+)(.*)', raw)
    if m:
        code = m.group(1)
        name = m.group(2).lstrip('、_ ')
        return code, name
    return None, None


class TimeoutException(Exception):
    pass


def query_industry_for_symbol(bs_code: str, logger) -> dict:
    """查询单只股票的行业信息，带 SIGALRM 超时"""
    def timeout_handler(signum, frame):
        raise TimeoutException(f"查询超时 {bs_code}")

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(QUERY_TIMEOUT))
    try:
        import time
        time.sleep(RATE_LIMIT_DELAY)
        rs = bs.query_stock_industry(code=bs_code)
        signal.alarm(0)
        if rs.error_code != '0':
            return None
        while rs.next():
            row = rs.get_row_data()
            industry_raw = row[3]
            classification = row[4]
            board_code, board_name = parse_industry(industry_raw)
            if board_code:
                return {
                    'board_code': board_code,
                    'board_name': board_name,
                    'board_type': 'INDUSTRY',
                    'industry_raw': industry_raw,
                    'classification': classification,
                }
        return None
    except TimeoutException:
        return {'__timeout__': True}
    except Exception as e:
        signal.alarm(0)
        return {'__error__': str(e)}
    finally:
        signal.signal(signal.SIGALRM, old_handler)


def get_all_listed_symbols(conn) -> list:
    """从数据库读取所有在市股票"""
    cur = conn.cursor()
    cur.execute("SELECT symbol FROM dwd_security_master WHERE status = 'LISTED'")
    rows = cur.fetchall()
    cur.close()
    return [r[0] for r in rows]


def upsert_board_master(conn, records: list) -> int:
    """批量 Upsert 板块主数据"""
    if not records:
        return 0
    cur = conn.cursor()
    sql = """
    INSERT INTO dwd_board_master
        (board_code, board_name, board_type, is_active, source, updated_at)
    VALUES %s
    ON CONFLICT (board_code) DO UPDATE SET
        board_name = EXCLUDED.board_name,
        board_type = EXCLUDED.board_type,
        is_active = EXCLUDED.is_active,
        source = EXCLUDED.source,
        updated_at = EXCLUDED.updated_at
    """
    now = datetime.now()
    values = [
        (
            r['board_code'],
            r['board_name'],
            r['board_type'],
            True,
            'baostock',
            now,
        )
        for r in records
    ]
    for i in range(0, len(values), BATCH_SIZE):
        batch = values[i:i + BATCH_SIZE]
        execute_values(cur, sql, batch)
        conn.commit()
    cur.close()
    return len(values)


def sync_board() -> dict:
    """
    同步板块主数据。
    返回: {"boards": 写入板块数}
    """
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("【板块主数据同步】开始")

    conn = psycopg2.connect(**DB_CONFIG)
    symbols = get_all_listed_symbols(conn)
    logger.info(f"在市股票共 {len(symbols)} 只，开始查询行业...")
    conn.close()

    bs.login()

    industry_map = {}
    timeout_count = 0
    error_count = 0

    for i, symbol in enumerate(symbols):
        if i % 100 == 0:
            logger.info(f"  查询进度: {i}/{len(symbols)}, 当前成功: {len(industry_map)}, 超时: {timeout_count}, 失败: {error_count}")

        bs_code = to_baostock_code(symbol)
        result = query_industry_for_symbol(bs_code, logger)

        if result is None:
            error_count += 1
        elif isinstance(result, dict) and result.get('__timeout__'):
            timeout_count += 1
        elif isinstance(result, dict) and result.get('__error__'):
            error_count += 1
        elif result:
            board_code = result.get('board_code')
            if board_code and board_code not in industry_map:
                industry_map[board_code] = {
                    'board_code': board_code,
                    'board_name': result['board_name'],
                    'board_type': result['board_type'],
                }

    logger.info(f"Baostock 查询完成，成功: {len(industry_map)}, 超时: {timeout_count}, 失败: {error_count}")

    bs.logout()

    if not industry_map:
        logger.warning("未获取到任何行业数据")
        return {"boards": 0}

    records = list(industry_map.values())
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        written = upsert_board_master(conn, records)
        logger.info(f"【板块主数据同步】完成，写入 {written} 条记录")
        return {"boards": written}
    finally:
        conn.close()


# ========== CLI 入口 ==========
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='板块主数据同步脚本')
    args = parser.parse_args()

    try:
        result = sync_board()
        print(f"\n完成，共写入 {result['boards']} 条板块记录")
    except Exception as e:
        print(f"\n失败: {e}")
        sys.exit(1)
