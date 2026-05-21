#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ETL Script: 同步 dwd_board_relation 股票-板块关系

数据来源:
- query_stock_industry: 查询每只股票的行业分类
- 全量股票从 dwd_security_master 读取
- board_code 从 dwd_board_master 验证存在

目标表: dwd_board_relation
主键: (trade_date, symbol, board_code)
板块类型: INDUSTRY（证监会行业分类）

用法:
    python sync_board_relation.py
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

RATE_LIMIT_DELAY = float(os.environ.get('SYNC_RATE_DELAY', '0.02'))
BATCH_SIZE = 200
LOG_DIR = os.environ.get('SYNC_LOG_DIR', '/app/logs')
QUERY_TIMEOUT = float(os.environ.get('SYNC_QUERY_TIMEOUT', '10'))


# ========== 日志 ==========
def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"sync_board_relation_{datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger('sync_board_relation')


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


def query_industry_for_symbol(bs_code: str) -> dict:
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
            board_code, board_name = parse_industry(industry_raw)
            if board_code:
                return {
                    'board_code': board_code,
                    'board_name': board_name,
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


def get_existing_board_codes(conn) -> set:
    """获取 dwd_board_master 中所有有效的 board_code"""
    cur = conn.cursor()
    cur.execute("SELECT board_code FROM dwd_board_master WHERE is_active = true")
    rows = cur.fetchall()
    cur.close()
    return {r[0] for r in rows}


def get_latest_trade_date(conn) -> str:
    """获取最近一个交易日（作为快照日期）"""
    cur = conn.cursor()
    cur.execute("""
        SELECT trade_date FROM dwd_trade_calendar
        WHERE exchange = 'SH' AND is_open = true
        ORDER BY trade_date DESC LIMIT 1
    """)
    row = cur.fetchone()
    cur.close()
    return row[0].strftime('%Y-%m-%d') if row else datetime.now().strftime('%Y-%m-%d')


def upsert_board_relation(conn, records: list) -> int:
    """批量 Upsert 股票-板块关系"""
    if not records:
        return 0
    cur = conn.cursor()
    sql = """
    INSERT INTO dwd_board_relation
        (symbol, board_code, board_type, relation_source, updated_at)
    VALUES %s
    ON CONFLICT (symbol, board_code) DO NOTHING
    """
    now = datetime.now()
    values = [
        (
            r['symbol'],
            r['board_code'],
            'INDUSTRY',
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


def sync_board_relation() -> dict:
    """
    同步股票-板块关系。
    返回: {"relations": 写入关联数}
    """
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("【股票-板块关系同步】开始")

    conn = psycopg2.connect(**DB_CONFIG)
    symbols = get_all_listed_symbols(conn)
    board_codes = get_existing_board_codes(conn)
    trade_date = get_latest_trade_date(conn)
    logger.info(f"在市股票共 {len(symbols)} 只，有效板块 {len(board_codes)} 个，快照日期 {trade_date}")
    conn.close()

    if not board_codes:
        logger.warning("dwd_board_master 中没有有效板块，先运行 sync_board.py")
        return {"relations": 0}

    bs.login()

    relations = []
    timeout_count = 0
    error_count = 0
    skipped = 0

    for i, symbol in enumerate(symbols):
        if i % 100 == 0:
            logger.info(f"  查询进度: {i}/{len(symbols)}, 当前成功: {len(relations)}, 超时: {timeout_count}, 失败: {error_count}, 跳过: {skipped}")

        bs_code = to_baostock_code(symbol)
        result = query_industry_for_symbol(bs_code)

        if result is None:
            error_count += 1
        elif isinstance(result, dict) and result.get('__timeout__'):
            timeout_count += 1
        elif isinstance(result, dict) and result.get('__error__'):
            error_count += 1
        elif result:
            board_code = result.get('board_code')
            # 只写入 board_master 中已存在的板块
            if board_code and board_code in board_codes:
                relations.append({
                    'symbol': symbol,
                    'board_code': board_code,
                })
            else:
                skipped += 1

    logger.info(f"Baostock 查询完成，成功: {len(relations)}, 超时: {timeout_count}, 失败: {error_count}, 跳过(板块未同步): {skipped}")

    bs.logout()

    if not relations:
        logger.warning("未获取到任何有效的股票-板块关系")
        return {"relations": 0}

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        written = upsert_board_relation(conn, relations)
        logger.info(f"【股票-板块关系同步】完成，写入 {written} 条记录（快照日期 {trade_date}）")
        return {"relations": written}
    finally:
        conn.close()


# ========== CLI 入口 ==========
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='股票-板块关系同步脚本')
    args = parser.parse_args()

    try:
        result = sync_board_relation()
        print(f"\n完成，共写入 {result['relations']} 条股票-板块关系记录")
    except Exception as e:
        print(f"\n失败: {e}")
        sys.exit(1)