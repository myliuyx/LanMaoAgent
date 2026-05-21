"""
测试同步复权因子数据

数据来源: baostock
- query_adjust_factor: 提供 adj_factor, foreAdjustFactor, backAdjustFactor
- query_dividend_data: 提供 cash_dividend, stock_dividend, rights_issue_ratio, event_type

数据库表: dwd_stock_adjust_factor

字段对应关系:
  trade_date        <- dividOperateDate (除权除息日)
  symbol            <- code (转换格式: sz.002131 -> 002131.SZ)
  adj_factor        <- foreAdjustFactor
  forward_adj_close <- foreAdjustFactor * 当前收盘价 (或直接用 baostock 的值)
  backward_adj_close <- backAdjustFactor * 当前收盘价
  cash_dividend     <- dividCashPsAfterTax (税后每股现金分红)
  stock_dividend    <- dividStocksPs (每股送股比例) + dividReserveToStockPs (转增比例)
  rights_issue_ratio <- (需另外计算或留空)
  event_type        <- 根据 cash_dividend/stock_dividend 判断事件类型
  source            <- 'baostock'

event_type 判断:
  - CASH_DIVIDEND: 只有现金分红
  - BONUS_SHARE: 只有送股
  - RESERVE_TO_STOCK: 只有转增
  - BONUS_SHARE_WITH_CASH: 送股+派现
  - RIGHTS_ISSUE: 配股
"""

import sys
sys.path.insert(0, '/home/huajuan/Github_Code/stock-fast-api')

from sqlalchemy import create_engine, text
import baostock as bs
import pandas as pd
from datetime import datetime

DB_URL = "postgresql+psycopg2://postgres:H7k9P2mX5wR1@192.168.3.16:5432/stock_cache_system"


def get_bao_code(symbol: str) -> str:
    """转换股票代码格式: 002131.SZ -> sz.002131"""
    if symbol.startswith('688'):
        return f'sh.{symbol[:6]}'
    elif symbol.startswith('603'):
        return f'sh.{symbol[:6]}'
    elif symbol.startswith('002') or symbol.startswith('300'):
        return f'sz.{symbol[:6]}'
    elif symbol.startswith('000') or symbol.startswith('001'):
        return f'sz.{symbol[:6]}'
    elif symbol.startswith('601') or symbol.startswith('600'):
        return f'sh.{symbol[:6]}'
    return None


def get_db_symbol(bao_code: str) -> str:
    """转换股票代码格式: sz.002131 -> 002131.SZ"""
    prefix = bao_code[:2]  # 'sz' or 'sh'
    num = bao_code[3:]
    return f'{num}.{prefix.upper()}'


def parse_dividend_value(val):
    """解析分红数据，处理 '0.045或0.0475' 这样的格式"""
    if val is None or pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    # 处理字符串
    val = str(val)
    if '或' in val:
        val = val.split('或')[0]
    try:
        return float(val)
    except:
        return 0.0


def get_event_type(cash_dividend: float, stock_dividend: float, reserve_to_stock: float, rights_issue: float) -> str:
    """根据分红送转数据判断事件类型"""
    # 先判断是否有配股
    if rights_issue and rights_issue > 0:
        return 'RIGHTS_ISSUE'

    has_cash = cash_dividend and cash_dividend > 0
    has_bonus = stock_dividend and stock_dividend > 0
    has_reserve = reserve_to_stock and reserve_to_stock > 0

    if has_bonus or has_reserve:
        if has_cash:
            return 'BONUS_SHARE_WITH_CASH'
        return 'BONUS_SHARE' if has_bonus else 'RESERVE_TO_STOCK'

    if has_cash:
        return 'CASH_DIVIDEND'

    return 'OTHER'


def test_query_adjust_factor():
    """测试 baostock query_adjust_factor API"""
    print("=" * 60)
    print("测试 query_adjust_factor")
    print("=" * 60)

    lg = bs.login()
    print(f"登录: {lg.error_msg}")

    # 测试一只股票
    bao_code = 'sz.002131'
    rs = bs.query_adjust_factor(bao_code, start_date='2015-01-01', end_date='2026-12-31')

    data_list = []
    while (rs.error_code == '0') and rs.next():
        data_list.append(rs.get_row_data())

    df = pd.DataFrame(data_list, columns=rs.fields)
    print(f"\n{bao_code} 复权因子历史 (共 {len(df)} 条):")
    print(df.to_string())

    bs.logout()
    print("\n✅ query_adjust_factor 测试通过")


def test_query_dividend_data():
    """测试 baostock query_dividend_data API"""
    print("\n" + "=" * 60)
    print("测试 query_dividend_data")
    print("=" * 60)

    lg = bs.login()
    print(f"登录: {lg.error_msg}")

    # 测试一只股票
    bao_code = 'sz.002131'
    rs = bs.query_dividend_data(bao_code, year='2015')

    data_list = []
    while (rs.error_code == '0') and rs.next():
        data_list.append(rs.get_row_data())

    df = pd.DataFrame(data_list, columns=rs.fields)
    print(f"\n{bao_code} 2015年分红数据 (共 {len(df)} 条):")
    print(df.to_string())

    # 查看所有字段
    print(f"\n字段说明:")
    for f in rs.fields:
        print(f"  {f}")

    bs.logout()
    print("\n✅ query_dividend_data 测试通过")


def test_sync_single_stock(symbol: str):
    """测试同步单只股票的复权因子数据"""
    print("\n" + "=" * 60)
    print(f"测试同步 {symbol}")
    print("=" * 60)

    bao_code = get_bao_code(symbol)
    if not bao_code:
        print(f"❌ 无法转换股票代码: {symbol}")
        return

    lg = bs.login()

    # 1. 获取复权因子
    rs_adj = bs.query_adjust_factor(bao_code, start_date='2010-01-01', end_date='2026-12-31')
    adj_list = []
    while (rs_adj.error_code == '0') and rs_adj.next():
        adj_list.append(rs_adj.get_row_data())
    adj_df = pd.DataFrame(adj_list, columns=rs_adj.fields)

    # 2. 获取分红数据
    years = range(2010, 2027)
    div_list = []
    for year in years:
        rs_div = bs.query_dividend_data(bao_code, year=str(year))
        while (rs_div.error_code == '0') and rs_div.next():
            div_list.append(rs_div.get_row_data())

    div_df = pd.DataFrame(div_list, columns=rs_div.fields)

    bs.logout()

    print(f"\n复权因子记录: {len(adj_df)} 条")
    if len(adj_df) > 0:
        print(adj_df.head().to_string())

    print(f"\n分红数据记录: {len(div_df)} 条")
    if len(div_df) > 0:
        print(div_df.head().to_string())

    # 3. 合并数据
    # adj_df: dividOperateDate, foreAdjustFactor, backAdjustFactor, adjustFactor
    # div_df: dividOperateDate, dividCashPsAfterTax, dividStocksPs, dividReserveToStockPs

    if len(div_df) > 0:
        # 处理 cash_dividend 字段中的 '0.045或0.0475' 格式
        div_df['cash_dividend'] = div_df['dividCashPsAfterTax'].apply(parse_dividend_value)
        div_df['stock_dividend'] = div_df['dividStocksPs'].apply(parse_dividend_value)
        div_df['reserve_to_stock'] = div_df['dividReserveToStockPs'].apply(parse_dividend_value)

        div_df = div_df.rename(columns={
            'dividOperateDate': 'trade_date'
        })
        adj_df = adj_df.rename(columns={
            'foreAdjustFactor': 'adj_factor',
            'dividOperateDate': 'trade_date'
        })

        # 合并
        merged = adj_df.merge(div_df[['trade_date', 'cash_dividend', 'stock_dividend', 'reserve_to_stock']],
                              on='trade_date', how='left')

        # 计算 event_type
        merged['event_type'] = merged.apply(
            lambda row: get_event_type(
                parse_dividend_value(row.get('cash_dividend')),
                parse_dividend_value(row.get('stock_dividend')),
                parse_dividend_value(row.get('reserve_to_stock')),
                0  # rights_issue 暂无
            ), axis=1
        )

        print(f"\n合并后数据 ({len(merged)} 条):")
        print(merged[['trade_date', 'adj_factor', 'cash_dividend', 'stock_dividend', 'event_type']].to_string())
    else:
        print("\n无分红数据，仅有复权因子记录")


def test_db_connection():
    """测试数据库连接"""
    print("\n" + "=" * 60)
    print("测试数据库连接")
    print("=" * 60)

    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) as cnt FROM dwd_security_master"))
        count = result.fetchone()[0]
        print(f"✅ 数据库连接正常: dwd_security_master 共 {count} 条记录")

    return engine


if __name__ == "__main__":
    print("开始测试复权因子同步...")
    print()

    # 1. 测试数据库连接
    engine = test_db_connection()

    # 2. 测试 baostock API
    test_query_adjust_factor()
    test_query_dividend_data()

    # 3. 测试单只股票同步
    test_sync_single_stock('002131.SZ')

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)