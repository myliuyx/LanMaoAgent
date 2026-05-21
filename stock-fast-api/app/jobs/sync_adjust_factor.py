"""
ETL Script: 从 Baostock 同步 dwd_stock_adjust_factor 复权因子表

数据来源:
- query_adjust_factor: 复权因子 (foreAdjustFactor, backAdjustFactor)
- query_dividend_data: 分红送转数据 (cash_dividend, stock_dividend, reserve_to_stock)

目标表: dwd_stock_adjust_factor
主键: (trade_date, symbol)

event_type 判断:
  - CASH_DIVIDEND: 只有现金分红
  - BONUS_SHARE: 只有送股（含转增）
  - BONUS_SHARE_WITH_CASH: 送股(含转增)+派现
  - STOCK_SPLIT: 股票拆分（无现金无送股但 adj_factor != 1）
  - OTHER: 其他

adj_factor 来源: foreAdjustFactor (Baostock 前复权因子)
forward_adj_close / backward_adj_close: 保留为空（Baostock 无真实价格数据，现有不准确）
rights_issue_ratio: 保留为空（Baostock 无此字段）
"""

import baostock as bs
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, date
import time
import os
import sys

# ========== 配置 ==========
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '192.168.3.16'),
    'port': int(os.environ.get('DB_PORT', '5432')),
    'database': os.environ.get('DB_NAME', 'stock_cache_system'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', '')
}

SYNC_START_YEAR = int(os.environ.get('SYNC_START_YEAR', '2010'))
SYNC_END_YEAR = int(os.environ.get('SYNC_END_YEAR', '2026'))
RATE_LIMIT_DELAY = float(os.environ.get('SYNC_RATE_DELAY', '0.05'))
BATCH_SIZE = 500
LOG_DIR = os.environ.get('SYNC_LOG_DIR', '/app/logs')

# ========== 工具函数 ==========

def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f'sync_adjust_factor_{datetime.now().strftime("%Y%m%d")}.log')
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger('sync_adjust_factor')


def to_baostock_code(symbol: str) -> str:
    """standard symbol -> baostock code, e.g. 600519.SH -> sh.600519"""
    ticker, exchange = symbol.split('.')
    mapping = {'SH': 'sh', 'SZ': 'sz', 'BJ': 'bj'}
    return f"{mapping.get(exchange, 'sh')}.{ticker}"


def to_symbol(bao_code: str) -> str:
    """baostock code -> standard symbol, e.g. sz.000001 -> 000001.SZ"""
    prefix = bao_code[:2]
    num = bao_code[3:]
    exchange = {'sh': 'SH', 'sz': 'SZ', 'bj': 'BJ'}.get(prefix, 'SH')
    return f"{num.zfill(6)}.{exchange}"


def parse_dividend_value(val):
    """解析分红数据，处理 '0.045或0.0475' 或空字符串格式"""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val = str(val).strip()
    if not val or val == 'None' or val == '':
        return 0.0
    if '或' in val:
        val = val.split('或')[0]
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def get_event_type(cash_dividend: float, stock_dividend: float, reserve_to_stock: float) -> str:
    """根据分红送转数据判断事件类型"""
    has_cash = cash_dividend and cash_dividend > 0
    has_bonus = stock_dividend and stock_dividend > 0
    has_reserve = reserve_to_stock and reserve_to_stock > 0

    if has_bonus or has_reserve:
        return 'BONUS_SHARE_WITH_CASH' if has_cash else 'BONUS_SHARE'
    if has_cash:
        return 'CASH_DIVIDEND'
    return 'OTHER'


def fetch_adjust_factor(bao_code: str, start_year: int, end_year: int) -> list:
    """获取指定年份范围的复权因子数据"""
    records = []
    for year in range(start_year, end_year + 1):
        rs = bs.query_adjust_factor(bao_code, start_date=f'{year}-01-01', end_date=f'{year}-12-31')
        while rs.error_code == '0' and rs.next():
            records.append(rs.get_row_data())
        time.sleep(RATE_LIMIT_DELAY)
    return records


def fetch_dividend_data(bao_code: str, start_year: int, end_year: int) -> list:
    """获取指定年份范围的分红数据"""
    records = []
    for year in range(start_year, end_year + 1):
        rs = bs.query_dividend_data(bao_code, year=str(year))
        while rs.error_code == '0' and rs.next():
            records.append(rs.get_row_data())
        time.sleep(RATE_LIMIT_DELAY)
    return records


def get_all_listed_symbols(conn) -> list:
    """获取所有在市股票代码"""
    cur = conn.cursor()
    cur.execute("SELECT symbol FROM dwd_security_master WHERE status = 'LISTED' ORDER BY symbol")
    symbols = [row[0] for row in cur.fetchall()]
    cur.close()
    return symbols


def get_existing_records(conn, symbol: str, start_year: int, end_year: int) -> set:
    """获取某只股票在指定年份范围内已有的 (trade_date, symbol) 集合"""
    cur = conn.cursor()
    cur.execute("""
        SELECT trade_date FROM dwd_stock_adjust_factor
        WHERE symbol = %s
          AND EXTRACT(YEAR FROM trade_date) BETWEEN %s AND %s
    """, (symbol, start_year, end_year))
    existing = {row[0] for row in cur.fetchall()}
    cur.close()
    return existing


def upsert_records(conn, records: list) -> int:
    """批量 Upsert 复权因子数据"""
    if not records:
        return 0
    cur = conn.cursor()
    upsert_sql = """
    INSERT INTO dwd_stock_adjust_factor (
        trade_date, symbol, adj_factor,
        cash_dividend, stock_dividend,
        event_type, source, updated_at
    ) VALUES %s
    ON CONFLICT (trade_date, symbol) DO UPDATE SET
        adj_factor = EXCLUDED.adj_factor,
        cash_dividend = EXCLUDED.cash_dividend,
        stock_dividend = EXCLUDED.stock_dividend,
        event_type = EXCLUDED.event_type,
        source = EXCLUDED.source,
        updated_at = NOW()
    """
    written = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i+BATCH_SIZE]
        try:
            execute_values(cur, upsert_sql, batch)
            conn.commit()
            written += len(batch)
        except Exception as e:
            conn.rollback()  # 失败时回滚，避免事务 abort 状态影响后续
            raise e
    cur.close()
    return written


def main():
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    logger = setup_logging()
    start_time = datetime.now()

    logger.info("=" * 70)
    logger.info("  复权因子同步 (dwd_stock_adjust_factor)")
    logger.info(f"  数据源: Baostock query_adjust_factor + query_dividend_data")
    logger.info(f"  同步范围: {SYNC_START_YEAR} ~ {SYNC_END_YEAR}")
    logger.info("=" * 70)

    bs.login()

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        symbols = get_all_listed_symbols(conn)
        total_stocks = len(symbols)

        logger.info(f"\n[配置] 在市股票: {total_stocks} 只, 同步年份: {SYNC_START_YEAR}-{SYNC_END_YEAR}")

        total_written = 0
        total_skipped = 0
        total_errors = 0

        logger.info("\n[开始同步]")
        logger.info("-" * 70)

        for idx, symbol in enumerate(symbols):
            bao_code = to_baostock_code(symbol)

            try:
                # 1. 获取复权因子
                adj_records = fetch_adjust_factor(bao_code, SYNC_START_YEAR, SYNC_END_YEAR)
                if not adj_records:
                    time.sleep(RATE_LIMIT_DELAY)
                    continue

                # 构建 adj_factor 字典: trade_date -> adj_factor
                adj_map = {}
                adj_fields = ['code', 'dividOperateDate', 'foreAdjustFactor', 'backAdjustFactor', 'adjustFactor']
                for row in adj_records:
                    # 跳过 adj_factor 为空或无效的记录
                    try:
                        adj_val = parse_dividend_value(row[2])
                        if adj_val == 0:
                            continue
                        trade_date = datetime.strptime(row[1], '%Y-%m-%d').date()
                        adj_map[trade_date] = adj_val
                    except (ValueError, IndexError):
                        continue

                if not adj_map:
                    continue

                # 2. 获取分红数据（用于 event_type 判断）
                div_records = fetch_dividend_data(bao_code, SYNC_START_YEAR, SYNC_END_YEAR)
                div_fields = ['code', 'dividPreNoticeDate', 'dividAgmPumDate', 'dividPlanAnnounceDate',
                              'dividPlanDate', 'dividRegistDate', 'dividOperateDate', 'dividPayDate',
                              'dividStockMarketDate', 'dividCashPsBeforeTax', 'dividCashPsAfterTax',
                              'dividStocksPs', 'dividCashStock', 'dividReserveToStockPs']

                # 构建 dividend 字典: trade_date -> (cash, stock, reserve)
                div_map = {}
                for row in div_records:
                    try:
                        trade_date = datetime.strptime(row[6], '%Y-%m-%d').date()
                        cash = parse_dividend_value(row[10])  # dividCashPsAfterTax
                        stock = parse_dividend_value(row[12])  # dividStocksPs
                        reserve = parse_dividend_value(row[13])  # dividReserveToStockPs
                        div_map[trade_date] = (cash, stock, reserve)
                    except (ValueError, IndexError):
                        continue

                # 3. 合并数据并写入
                write_records = []
                for trade_date, adj_factor in adj_map.items():
                    cash, stock, reserve = div_map.get(trade_date, (0.0, 0.0, 0.0))

                    # 判断 event_type
                    if adj_factor != 1.0 and cash == 0.0 and stock == 0.0 and reserve == 0.0:
                        event_type = 'STOCK_SPLIT'
                    else:
                        event_type = get_event_type(cash, stock, reserve)

                    write_records.append((
                        trade_date,
                        symbol,
                        adj_factor,
                        cash if cash > 0 else None,
                        stock if stock > 0 else None,
                        event_type,
                        'baostock',
                        datetime.now(),
                    ))

                # 4. Upsert
                if write_records:
                    written = upsert_records(conn, write_records)
                    total_written += written

            except Exception as e:
                total_errors += 1
                logger.warning(f"  处理失败 {symbol}: {e}")
                try:
                    conn.rollback()  # 回滚 abort 状态的事务，避免影响后续股票
                except Exception:
                    pass

            # 进度输出
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = total_written / elapsed if elapsed > 0 else 0
            if (idx + 1) % 100 == 0 or idx == total_stocks - 1:
                logger.info(
                    f"  [{idx+1:4d}/{total_stocks}] {symbol}: "
                    f"累计写入 {total_written} 条 错误 {total_errors} 条 | {rate:.1f} 条/秒"
                )

            time.sleep(RATE_LIMIT_DELAY)

        conn.close()

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("-" * 70)
        logger.info(f"[同步完成] 总耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
        logger.info(f"  总写入: {total_written} 条")
        logger.info(f"  总错误: {total_errors} 条")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"同步失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        bs.logout()


if __name__ == '__main__':
    main()