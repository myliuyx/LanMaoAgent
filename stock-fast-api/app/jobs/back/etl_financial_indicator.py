"""
[已废弃] 此脚本与主版 etl_financial_indicator.py 存在公式分歧 (ROA/BPS 计算错误)，请勿使用。
预计删除时间：2026Q3

ETL Script: 从 Baostock 回填 dwd_stock_financial_indicator 表

数据来源映射:
- query_profit_data:  roeAvg->roe, npMargin->net_margin, gpMargin->gross_margin,
                       netProfit->net_profit, MBRevenue->revenue, epsTTM->eps,
                       totalShare->total_share, liqaShare->liqa_share
- query_balance_data: liabilityToAsset->debt_to_asset, currentRatio->current_ratio, quickRatio->quick_ratio
- query_growth_data:  YOYNI->net_profit_yoy
- query_dupont_data:  dupontROE->roe, dupontAssetTurn->roa (间接)

注意:
- Baostock 的 roeAvg, npMargin, gpMargin, liabilityToAsset 本身就是百分数格式 (如 8.45 表示 8.45%)
- currentRatio, quickRatio 是倍数，不是百分数
- YOYNI 是小数格式 (如 0.15 表示 15%)，需要转换
- ocf, revenue_yoy: Baostock 未提供，保留为空
"""

import baostock as bs
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, date
import time
import os
import sys


DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '192.168.3.16'),
    'port': int(os.environ.get('DB_PORT', '5432')),
    'database': os.environ.get('DB_NAME', 'stock_cache_system'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', '')
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def convert_code_to_symbol(code):
    """baostock code 转换为标准 symbol 格式，如 sz.000001 -> 000001.SZ"""
    code = code.lower()
    if code.startswith('sh.'):
        return code[3:].zfill(6) + '.SH'
    elif code.startswith('sz.'):
        return code[3:].zfill(6) + '.SZ'
    elif code.startswith('bj.'):
        return code[3:].zfill(6) + '.BJ'
    return code

def get_report_type(stat_date_str):
    """根据 statDate 判断报告期类型

    注意：Baostock 返回的利润表数据是累计值：
    - Q1(3月): 一季度数据
    - Q2(6月): 半年累计数据
    - Q3(9月): 三季度累计数据
    - Q4(12月): 全年累计数据

    但财务报表习惯上：
    - 一季报(Q1): 截至3月底
    - 半年报(H1): 截至6月底（不是Q2）
    - 三季报(Q3): 截至9月底（不是Q3）
    - 年报(annual): 截至12月底

    我们需要正确区分 Q2 和 H1：Q2 单独表示二季度数据（4-6月），H1 是半年度累计
    """
    month = int(stat_date_str[5:7])
    if month == 3:
        return 'Q1'
    elif month == 6:
        return 'H1'
    elif month == 9:
        return 'Q3'
    elif month == 12:
        return 'annual'
    return 'annual'

def to_percent(val, max_val=None):
    """将小数转为百分数，如 0.15 -> 15.0
    如果值超过 max_val，返回 None（视为异常值）
    """
    if val is None:
        return None
    result = round(val * 100, 4)
    if max_val is not None and abs(result) > max_val:
        return None
    return result

def parse_float(val):
    """解析浮点数，空字符串或None返回None"""
    if val is None or val == '' or val == 'None':
        return None
    try:
        return float(val)
    except:
        return None

def fetch_profit_data(code, year, quarter):
    """获取利润表数据"""
    rs = bs.query_profit_data(code=code, year=year, quarter=quarter)
    data_list = []
    if rs.error_code != '0':
        return [], []
    while rs.next():
        data_list.append(rs.get_row_data())
    return data_list, rs.fields

def fetch_balance_data(code, year, quarter):
    """获取资产负债表数据"""
    rs = bs.query_balance_data(code=code, year=year, quarter=quarter)
    data_list = []
    if rs.error_code != '0':
        return [], []
    while rs.next():
        data_list.append(rs.get_row_data())
    return data_list, rs.fields

def fetch_growth_data(code, year, quarter):
    """获取成长能力数据"""
    rs = bs.query_growth_data(code=code, year=year, quarter=quarter)
    data_list = []
    if rs.error_code != '0':
        return [], []
    while rs.next():
        data_list.append(rs.get_row_data())
    return data_list, rs.fields

def fetch_dupont_data(code, year, quarter):
    """获取杜邦分析数据"""
    rs = bs.query_dupont_data(code=code, year=year, quarter=quarter)
    data_list = []
    if rs.error_code != '0':
        return [], []
    while rs.next():
        data_list.append(rs.get_row_data())
    return data_list, rs.fields
    data_list = []
    while rs.error_code == '0' and rs.next():
        data_list.append(rs.get_row_data())
    return data_list, rs.fields

def fetch_all_financial_data(code, year, quarter):
    """获取某股票某季度所有财务数据并合并"""
    result = {
        'code': code,
        'statDate': None,
        'report_period': None,
        'report_type': None,
        'announce_date': None,
        'eps': None,
        'bps': None,
        'roe': None,
        'roa': None,
        'gross_margin': None,
        'net_margin': None,
        'debt_to_asset': None,
        'current_ratio': None,
        'quick_ratio': None,
        'total_share': None,
        'liqa_share': None,
        'revenue': None,
        'net_profit': None,
        'revenue_yoy': None,
        'net_profit_yoy': None,
        'ocf': None,
        'ocf_to_revenue': None,
        'source': 'baostock'
    }

    profit_data, profit_fields = fetch_profit_data(code, year, quarter)
    balance_data, balance_fields = fetch_balance_data(code, year, quarter)
    growth_data, growth_fields = fetch_growth_data(code, year, quarter)
    dupont_data, dupont_fields = fetch_dupont_data(code, year, quarter)

    if profit_data:
        row = profit_data[0]
        result['statDate'] = row[profit_fields.index('statDate')]
        result['announce_date'] = row[profit_fields.index('pubDate')]
        result['report_type'] = get_report_type(result['statDate'])
        try:
            result['report_period'] = datetime.strptime(result['statDate'], '%Y-%m-%d').date()
        except ValueError:
            result['report_period'] = None

        # roeAvg, npMargin, gpMargin 是小数格式（如 0.067312 = 6.73%），需转百分数
        # 注意：Baostock 有时返回异常大的值（如 npMargin=-71560 表示 -71560%），
        # 超过 9999% 视为异常值，置为空
        result['roe'] = to_percent(parse_float(row[profit_fields.index('roeAvg')]), max_val=9999)
        result['net_margin'] = to_percent(parse_float(row[profit_fields.index('npMargin')]), max_val=9999)
        result['gross_margin'] = to_percent(parse_float(row[profit_fields.index('gpMargin')]), max_val=9999)
        result['net_profit'] = parse_float(row[profit_fields.index('netProfit')])
        result['revenue'] = parse_float(row[profit_fields.index('MBRevenue')])
        result['eps'] = parse_float(row[profit_fields.index('epsTTM')])
        result['total_share'] = parse_float(row[profit_fields.index('totalShare')])
        result['liqa_share'] = parse_float(row[profit_fields.index('liqaShare')])

    if balance_data:
        row = balance_data[0]
        # liabilityToAsset 是小数格式（如 0.05 = 5%），转百分数需 *100
        la = parse_float(row[balance_fields.index('liabilityToAsset')])
        # 负债率超过 100% 视为异常值（正常企业不会超过）
        if la is not None and la > 1.0:
            result['debt_to_asset'] = None
        else:
            result['debt_to_asset'] = to_percent(la, max_val=9999) if la is not None else None
        # currentRatio, quickRatio 是倍数，不是百分数
        result['current_ratio'] = parse_float(row[balance_fields.index('currentRatio')])
        result['quick_ratio'] = parse_float(row[balance_fields.index('quickRatio')])

    if growth_data:
        row = growth_data[0]
        # YOYNI 超过 1000% 视为异常值（Baostock 有时会返回极端值如 13500 表示 1350000%）
        result['net_profit_yoy'] = to_percent(parse_float(row[growth_fields.index('YOYNI')]), max_val=1000)
        # revenue_yoy: baostock query_growth_data 仅提供 YOYNI (净利润增速)
        # YOYEquity 是股东权益增速，不是收入增速，故不映射

    if dupont_data:
        row = dupont_data[0]
        dupont_roe = parse_float(row[dupont_fields.index('dupontROE')])
        if result['roe'] is None and dupont_roe is not None:
            # dupontROE 是小数格式，需转百分数
            result['roe'] = to_percent(dupont_roe)

        # roa 计算: dupontAssetTurn 是资产周转率(次数), roa ≈ 净利率 × 资产周转率
        asset_turn = parse_float(row[dupont_fields.index('dupontAssetTurn')])
        if result['roa'] is None and asset_turn is not None:
            net_margin_val = result['net_margin'] / 100 if result['net_margin'] else None
            if net_margin_val is not None:
                result['roa'] = round(net_margin_val * asset_turn * 100, 4)
            else:
                # 简化估算：资产周转率 × 10%
                result['roa'] = round(asset_turn * 10, 4)

    return result

def get_all_symbols(conn):
    """获取所有股票symbol列表"""
    cur = conn.cursor()
    cur.execute("SELECT symbol FROM dwd_security_master WHERE status = 'LISTED' ORDER BY symbol")
    symbols = [row[0] for row in cur.fetchall()]
    cur.close()
    return symbols

def symbol_to_baostock_code(symbol):
    """将标准symbol转换为baostock代码格式，如 000001.SZ -> sz.000001"""
    ticker = symbol.split('.')[0]
    exchange = symbol.split('.')[1]
    if exchange == 'SH':
        return f'sh.{ticker}'
    elif exchange == 'SZ':
        return f'sz.{ticker}'
    elif exchange == 'BJ':
        return f'bj.{ticker}'
    return None

def get_existing_quarters(conn, symbol):
    """获取某股票已存在的季度列表"""
    cur = conn.cursor()
    cur.execute(
        "SELECT report_period, report_type FROM dwd_stock_financial_indicator WHERE symbol = %s",
        (symbol,)
    )
    existing = set()
    for row in cur.fetchall():
        existing.add((row[0], row[1]))
    cur.close()
    return existing

def main():
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    # 支持 SKIP_FIRST 环境变量跳过前N只股票
    skip_first = int(os.environ.get('SKIP_FIRST', '0'))

    # 参数优先级：
    # 1. SYNC_YEAR + SYNC_QUARTER → 同步指定年/季度
    # 2. SYNC_START_YEAR + SYNC_END_YEAR → 同步区间内所有季度
    # 3. 都不设置 → 默认同步 2020~2026 全部季度
    sync_year = os.environ.get('SYNC_YEAR')
    sync_quarter = os.environ.get('SYNC_QUARTER')
    sync_start_year = os.environ.get('SYNC_START_YEAR')
    sync_end_year = os.environ.get('SYNC_END_YEAR')

    if sync_year and sync_quarter:
        years = [int(sync_year)]
        quarters = [int(sync_quarter)]
        mode = f'增量同步: {sync_year}年第{sync_quarter}季度'
    elif sync_start_year and sync_end_year:
        start_y = int(sync_start_year)
        end_y = int(sync_end_year)
        years = list(range(start_y, end_y + 1))
        quarters = [1, 2, 3, 4]
        mode = f'区间同步: {start_y}~{end_y}年'
    else:
        years = [2026, 2025, 2024, 2023, 2022, 2021, 2020]
        quarters = [1, 2, 3, 4]
        mode = '全量同步: 2020-2026'

    bs.login()
    print('=' * 70)
    print('  财务指标 ETL 同步任务')
    print('  数据源: Baostock')
    print('  目标表: dwd_stock_financial_indicator')
    print(f'  同步模式: {mode}')
    print('=' * 70, flush=True)

    conn = get_db_connection()
    symbols = get_all_symbols(conn)
    total_stocks = len(symbols)

    print(f'\n[配置]')
    print(f'  股票数量: {total_stocks}')
    print(f'  同步年份: {years}')
    print(f'  同步季度: {quarters}')
    print(f'  优化: 跳过已存在的季度数据')
    if skip_first > 0:
        print(f'  跳过前: {skip_first} 只股票')

    total_records = 0
    error_count = 0
    skip_count = 0
    start_time = datetime.now()

    print(f'\n[开始同步]', flush=True)
    print('-' * 70, flush=True)

    for idx, symbol in enumerate(symbols):
        # 跳过前N只股票
        if idx < skip_first:
            continue

        bs_code = symbol_to_baostock_code(symbol)
        if not bs_code:
            continue

        stock_records = 0
        stock_skip = 0

        # 获取已存在的季度，减少重复查询
        existing_quarters = get_existing_quarters(conn, symbol)

        for year in years:
            for quarter in quarters:
                # 映射 quarter 到 report_type
                report_type = {1: 'Q1', 2: 'H1', 3: 'Q3', 4: 'annual'}[quarter]

# 计算 report_period（用于判断是否已存在）
                month_day_map = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
                m, d = month_day_map[quarter]
                report_period = date(year, m, d)

                # 跳过已存在的季度
                if (report_period, report_type) in existing_quarters:
                    skip_count += 1
                    stock_skip += 1
                    continue

                try:
                    data = fetch_all_financial_data(bs_code, year, quarter)
                    if data['statDate'] is None or data['report_period'] is None:
                        continue

                    # 计算 bps: equity / total_share = (net_profit / roe) / total_share
                    if data['bps'] is None:
                        np = data['net_profit']
                        r = data['roe']
                        ts = data['total_share']
                        if np is not None and r is not None and r != 0 and ts is not None and ts != 0:
                            equity = np / (r / 100)  # roe 是百分数，转为小数
                            data['bps'] = round(equity / ts, 4)

                    cur = conn.cursor()
                    upsert_sql = """
                    INSERT INTO dwd_stock_financial_indicator
                    (symbol, report_period, report_type, announce_date, eps, bps, roe, roa,
                     gross_margin, net_margin, debt_to_asset, current_ratio, quick_ratio,
                     total_share, liqa_share, revenue, net_profit, revenue_yoy, net_profit_yoy,
                     ocf, ocf_to_revenue, source, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (symbol, report_period, report_type)
                    DO UPDATE SET
                        announce_date = EXCLUDED.announce_date,
                        eps = EXCLUDED.eps,
                        bps = EXCLUDED.bps,
                        roe = EXCLUDED.roe,
                        roa = EXCLUDED.roa,
                        gross_margin = EXCLUDED.gross_margin,
                        net_margin = EXCLUDED.net_margin,
                        debt_to_asset = EXCLUDED.debt_to_asset,
                        current_ratio = EXCLUDED.current_ratio,
                        quick_ratio = EXCLUDED.quick_ratio,
                        total_share = EXCLUDED.total_share,
                        liqa_share = EXCLUDED.liqa_share,
                        revenue = EXCLUDED.revenue,
                        net_profit = EXCLUDED.net_profit,
                        revenue_yoy = EXCLUDED.revenue_yoy,
                        net_profit_yoy = EXCLUDED.net_profit_yoy,
                        ocf = EXCLUDED.ocf,
                        ocf_to_revenue = EXCLUDED.ocf_to_revenue,
                        source = EXCLUDED.source,
                        updated_at = NOW()
                    """

                    cur.execute(upsert_sql, (
                        symbol,
                        data['report_period'],
                        data['report_type'],
                        data['announce_date'],
                        data['eps'],
                        data['bps'],
                        data['roe'],
                        data['roa'],
                        data['gross_margin'],
                        data['net_margin'],
                        data['debt_to_asset'],
                        data['current_ratio'],
                        data['quick_ratio'],
                        data['total_share'],
                        data['liqa_share'],
                        data['revenue'],
                        data['net_profit'],
                        data['revenue_yoy'],
                        data['net_profit_yoy'],
                        data['ocf'],
                        data['ocf_to_revenue'],
                        data['source']
                    ))
                    conn.commit()
                    cur.close()
                    total_records += 1
                    stock_records += 1

                except Exception as e:
                    error_count += 1
                    conn.rollback()  # 回滚失败的事务
                    print(f'  [错误] {symbol} {year}Q{quarter}: {e}', flush=True)

                time.sleep(0.05)

        # 每只股票完成后的日志
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = total_records / elapsed if elapsed > 0 else 0
        print(f'  [{idx+1:4d}/{total_stocks}] {symbol}: 新增{stock_records}条 跳过{stock_skip}条 | '
              f'累计{total_records}条 错误{error_count}条 | {rate:.1f}条/秒', flush=True)

    conn.close()
    bs.logout()

    elapsed = (datetime.now() - start_time).total_seconds()
    print('-' * 70)
    print('[同步完成]')
    print(f'  总耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)')
    print(f'  总记录: {total_records}条')
    print(f'  跳过: {skip_count}条')
    print(f'  错误数: {error_count}条')
    print(f'  平均速度: {total_records/elapsed:.1f}条/秒')
    print('=' * 70)

if __name__ == '__main__':
    main()