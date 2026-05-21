"""
ETL Script: 从 Baostock 同步 dwd_security_master 股票主数据

数据来源:
- query_stock_basic: 获取全量股票列表 (code, code_name, ipoDate, outDate, type, status)
- query_stock_industry: 获取行业分类 (industry, industryClassification)

优化策略:
- 增量同步: industry 查询只针对缺失数据的股票
- 并发: 使用 ProcessPoolExecutor 并行查询行业（进程隔离，可强制超时）
- 幂等写入: ON CONFLICT (symbol) DO UPDATE
"""
import baostock as bs
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import time
import re
import os
import sys
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

# ========== 配置 ==========
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '192.168.3.16'),
    'port': int(os.environ.get('DB_PORT', '5432')),
    'database': os.environ.get('DB_NAME', 'stock_cache_system'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', '')
}

MAX_WORKERS = int(os.environ.get('SYNC_WORKERS', '10'))  # 并发进程数
RATE_LIMIT_DELAY = float(os.environ.get('SYNC_RATE_DELAY', '0.02'))  # 每次请求间隔（秒）
BATCH_SIZE = 500  # 批量写入大小
LOG_DIR = os.environ.get('SYNC_LOG_DIR', '/app/logs')
QUERY_TIMEOUT = float(os.environ.get('SYNC_QUERY_TIMEOUT', '10'))  # 查询超时秒数


# ========== 工具函数 ==========

def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f'sync_security_master_{datetime.now().strftime("%Y%m%d")}.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger('sync_security_master')


def normalize_code(code: str) -> str:
    """baostock code -> standard symbol, e.g. sh.600519 -> 600519.SH"""
    code = code.lower()
    if code.startswith('sh.'):
        return code[3:].zfill(6) + '.SH'
    elif code.startswith('sz.'):
        return code[3:].zfill(6) + '.SZ'
    elif code.startswith('bj.'):
        return code[3:].zfill(6) + '.BJ'
    return code


def get_exchange(code: str) -> str:
    code = code.lower()
    if code.startswith('sh.'):
        return 'SH'
    elif code.startswith('sz.'):
        return 'SZ'
    elif code.startswith('bj.'):
        return 'BJ'
    return 'SH'


def get_security_type(symbol: str, bs_type: str) -> str:
    """根据 ticker 推断证券类型"""
    if bs_type != '1':
        return '未知'
    ticker = symbol.split('.')[0]
    if ticker.startswith('688'):
        return '科创板'
    elif ticker.startswith('002') or ticker.startswith('003'):
        return '创业板'
    elif ticker.startswith('8') or ticker.startswith('4'):
        return '北交所'
    else:
        return '主板'


def is_st(name: str) -> bool:
    return 'ST' in name or '*ST' in name or 'S*ST' in name


def clean_industry(raw: str) -> tuple:
    """从 'C15酒、饮料和精制茶制造业' 提取一级和二级行业"""
    if not raw:
        return None, None
    clean = re.sub(r'^[A-Z]\d+', '', raw).lstrip('_ ')
    parts = re.split(r'[、和]', clean, 1)
    l1 = parts[0] if parts else None
    l2 = parts[1] if len(parts) > 1 else None
    return l1, l2


def query_industry_worker(bs_code: str) -> dict:
    """
    在独立进程中查询股票行业（进程隔离，可强制超时）
    每个进程独立登录 baostock
    """
    try:
        bs.login()
        time.sleep(RATE_LIMIT_DELAY)
        rs = bs.query_stock_industry(code=bs_code)
        bs.logout()
        if rs.error_code != '0':
            return {'code': bs_code, 'industry_l1': None, 'industry_l2': None}
        while rs.next():
            row = rs.get_row_data()
            l1, l2 = clean_industry(row[3])
            return {'code': bs_code, 'industry_l1': l1, 'industry_l2': l2}
        return {'code': bs_code, 'industry_l1': None, 'industry_l2': None}
    except Exception as e:
        try:
            bs.logout()
        except:
            pass
        return {'__error__': str(e), 'code': bs_code}


def get_missing_symbols(conn, limit: int = None) -> list:
    """获取缺少行业信息的在市股票列表"""
    cur = conn.cursor()
    sql = """
        SELECT symbol, ticker, exchange
        FROM dwd_security_master
        WHERE status = 'LISTED'
          AND (industry_l1 IS NULL OR industry_l2 IS NULL)
    """
    if limit:
        sql += f" LIMIT {limit}"
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return [{'symbol': r[0], 'ticker': r[1], 'exchange': r[2]} for r in rows]


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


def upsert_security_master(conn, records: list) -> int:
    """批量 Upsert 股票主数据"""
    if not records:
        return 0
    cur = conn.cursor()
    upsert_sql = """
    INSERT INTO dwd_security_master (
        symbol, ticker, exchange, name, security_type,
        list_date, delist_date, status, is_st,
        industry_l1, industry_l2, source, updated_at
    ) VALUES %s
    ON CONFLICT (symbol) DO UPDATE SET
        ticker = EXCLUDED.ticker,
        exchange = EXCLUDED.exchange,
        name = EXCLUDED.name,
        security_type = EXCLUDED.security_type,
        list_date = EXCLUDED.list_date,
        delist_date = EXCLUDED.delist_date,
        status = EXCLUDED.status,
        is_st = EXCLUDED.is_st,
        industry_l1 = EXCLUDED.industry_l1,
        industry_l2 = EXCLUDED.industry_l2,
        source = EXCLUDED.source,
        updated_at = NOW()
    """
    written = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i+BATCH_SIZE]
        execute_values(cur, upsert_sql, batch)
        conn.commit()
        written += len(batch)
    cur.close()
    return written


def main():
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    logger = setup_logging()
    start_time = datetime.now()

    logger.info("=" * 70)
    logger.info("  股票主数据同步")
    logger.info(f"  数据源: Baostock query_stock_basic + query_stock_industry")
    logger.info(f"  目标表: dwd_security_master")
    logger.info(f"  并发进程数: {MAX_WORKERS}")
    logger.info(f"  请求间隔: {RATE_LIMIT_DELAY}s")
    logger.info(f"  查询超时: {QUERY_TIMEOUT}s")
    logger.info("=" * 70)

    bs.login()

    try:
        conn = psycopg2.connect(**DB_CONFIG)

        # ========== Step 1: 获取全量股票基础信息 ==========
        logger.info("\n[Step 1] 获取 Baostock 全量股票列表 (type=1)...")
        rs = bs.query_stock_basic(code='')
        stocks = []
        while rs.next():
            row = rs.get_row_data()
            bs_code, name, ipo_date, out_date, bs_type, bs_status = row
            if bs_type != '1':
                continue
            symbol = normalize_code(bs_code)
            ticker = symbol.split('.')[0]
            exchange = get_exchange(bs_code)
            status = 'LISTED' if bs_status == '1' else 'DELISTED'

            stocks.append({
                'symbol': symbol,
                'ticker': ticker,
                'exchange': exchange,
                'name': name,
                'security_type': get_security_type(symbol, bs_type),
                'list_date': ipo_date if ipo_date else None,
                'delist_date': out_date if out_date else None,
                'status': status,
                'is_st': is_st(name),
                'source': 'baostock',
                'updated_at': datetime.now(),
            })

        logger.info(f"  获取股票总数: {len(stocks)} (在市 {(sum(1 for s in stocks if s['status']=='LISTED'))} 只)")

        # ========== Step 2: 找出缺行业信息的股票，并发查询行业 ==========
        missing = get_missing_symbols(conn)
        logger.info(f"\n[Step 2] 缺行业信息股票: {len(missing)} 只")

        industry_results = {}  # symbol -> {industry_l1, industry_l2}
        if missing:
            bs_codes = [to_baostock_code(s['symbol']) for s in missing]
            symbols = [s['symbol'] for s in missing]

            logger.info(f"  并发查询行业中 (进程数={MAX_WORKERS})...")
            timeout_count = 0
            error_count = 0

            with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_symbol = {
                    executor.submit(query_industry_worker, bs_code): symbol
                    for bs_code, symbol in zip(bs_codes, symbols)
                }

                done = 0
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        result = future.result(timeout=QUERY_TIMEOUT + 1)
                        if result.get('__error__'):
                            error_count += 1
                            logger.warning(f"  查询行业失败 {symbol}: {result.get('__error__')}")
                        else:
                            industry_results[symbol] = result
                    except TimeoutError:
                        timeout_count += 1
                        logger.warning(f"  查询行业超时 {symbol}")
                    except Exception as e:
                        error_count += 1
                        logger.warning(f"  查询行业失败 {symbol}: {e}")
                    done += 1
                    if done % 500 == 0 or done == len(missing):
                        logger.info(f"  行业查询进度: {done}/{len(missing)}, 超时: {timeout_count}, 失败: {error_count}")

        logger.info(f"  行业查询完成，成功: {len(industry_results)}, 超时: {timeout_count}, 失败: {error_count}")

        # ========== Step 3: 合并行业信息到股票数据 ==========
        logger.info("\n[Step 3] 合并行业信息...")
        for s in stocks:
            if s['symbol'] in industry_results:
                ind = industry_results[s['symbol']]
                s['industry_l1'] = ind.get('industry_l1')
                s['industry_l2'] = ind.get('industry_l2')
            else:
                s['industry_l1'] = None
                s['industry_l2'] = None

        # ========== Step 4: Upsert 到数据库 ==========
        logger.info("\n[Step 4] 执行 Upsert...")
        records = [
            (
                s['symbol'], s['ticker'], s['exchange'], s['name'], s['security_type'],
                s['list_date'], s['delist_date'], s['status'], s['is_st'],
                s['industry_l1'], s['industry_l2'], s['source'], s['updated_at']
            )
            for s in stocks
        ]
        written = upsert_security_master(conn, records)
        logger.info(f"  写入记录数: {written}")

        conn.close()

        # ========== Step 5: 验证 ==========
        conn2 = psycopg2.connect(**DB_CONFIG)
        cur2 = conn2.cursor()
        cur2.execute("SELECT COUNT(*) FROM dwd_security_master")
        total = cur2.fetchone()[0]
        cur2.execute("SELECT COUNT(*) FROM dwd_security_master WHERE status = 'LISTED'")
        listed = cur2.fetchone()[0]
        cur2.execute("SELECT COUNT(*) FROM dwd_security_master WHERE status = 'LISTED' AND industry_l1 IS NOT NULL")
        has_industry = cur2.fetchone()[0]
        cur2.close()
        conn2.close()

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("\n=== 验证结果 ===")
        logger.info(f"  总记录数: {total}")
        logger.info(f"  在市(LISTED): {listed}")
        logger.info(f"  有行业信息: {has_industry}")
        logger.info(f"  总耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"同步失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        bs.logout()


if __name__ == '__main__':
    main()