"""
随机抽500只股票，取每只股票2条复权因子记录，与baostock对比验证准确性。

用法:
    ./venv/bin/python tests/validate_adjust_factor_batch.py
"""

import sys
sys.path.insert(0, '/home/huajuan/Github_Code/stock-fast-api')

import random
from sqlalchemy import create_engine, text
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta

DB_URL = "postgresql+psycopg2://postgres:H7k9P2mX5wR1@192.168.3.16:5432/stock_cache_system"

# baostock 前缀映射
BAO_PREFIX = {}
# 动态构建前缀映射 (sz.000xxx, sz.002xxx, sz.300xxx, sh.688xxx, sh.603xxx)
def get_bao_prefix(symbol):
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
    else:
        return None


def get_engine():
    return create_engine(DB_URL)


def random_date(start_year=2020, end_year=2025):
    """生成随机日期"""
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return (start + timedelta(days=random_days)).strftime('%Y-%m-%d')


def validate_single_with_baostock(symbol: str, trade_date: str, db_factor: float):
    """用 baostock 验证单条记录"""
    bao_code = get_bao_prefix(symbol)
    if not bao_code:
        return {'valid': False, 'error': 'unknown symbol prefix'}

    td = datetime.strptime(trade_date, '%Y-%m-%d')
    year, month = td.year, td.month
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-31"
    else:
        end = f"{year}-{month + 1:02}-31"

    rs = bs.query_adjust_factor(bao_code, start_date=start, end_date=end)
    data_list = []
    while (rs.error_code == '0') and rs.next():
        data_list.append(rs.get_row_data())
    df = pd.DataFrame(data_list, columns=rs.fields)

    bao_rec = df[df['dividOperateDate'] == trade_date]

    if len(bao_rec) == 0:
        return {'valid': False, 'error': 'no baostock record'}

    bao_val = float(bao_rec.iloc[0]['foreAdjustFactor'])
    diff_pct = abs(db_factor - bao_val) / bao_val * 100 if bao_val != 0 else 0

    return {
        'valid': True,
        'bao_factor': bao_val,
        'diff_pct': diff_pct,
        'needs_fix': diff_pct > 1.0,
    }


def main():
    engine = get_engine()

    print("=" * 80)
    print("随机抽500只股票 × 每只2条记录 = 约1000条数据与baostock对比")
    print("=" * 80)

    # 1. 随机选取500只有复权因子记录的股票
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT symbol FROM (
                SELECT DISTINCT symbol FROM dwd_stock_adjust_factor
            ) t
            ORDER BY RANDOM() LIMIT 500
        """))
        symbols = [row[0] for row in result.fetchall()]

    print(f"\n随机选取 {len(symbols)} 只股票\n")

    # 2. 登录 baostock
    lg = bs.login()
    print(f"baostock 登录: {lg.error_code} {lg.error_msg}")

    # 3. 每只股票随机取2条记录验证
    results = []
    errors = []
    checked = 0

    for i, symbol in enumerate(symbols):
        # 获取该股票所有复权因子记录
        with engine.connect() as conn:
            records = conn.execute(text("""
                SELECT trade_date, adj_factor, event_type
                FROM dwd_stock_adjust_factor
                WHERE symbol = :symbol
                ORDER BY trade_date
            """), {'symbol': symbol}).fetchall()

        if len(records) < 2:
            # 记录不足2条的，尝试从不同年份选取
            if len(records) == 1:
                records = [records[0]]
            else:
                continue

        # 随机选取2条记录（或1条）
        sample_size = min(2, len(records))
        sampled = random.sample(list(records), sample_size)

        for rec in sampled:
            td = rec.trade_date
            td_str = td.strftime('%Y-%m-%d') if hasattr(td, 'strftime') else str(td)
            if rec.adj_factor is None:
                continue
            db_factor = float(rec.adj_factor)

            result = validate_single_with_baostock(symbol, td_str, db_factor)
            result['symbol'] = symbol
            result['trade_date'] = td_str
            result['db_factor'] = db_factor
            result['event_type'] = rec.event_type

            if result['valid']:
                results.append(result)
                checked += 1
            else:
                errors.append(result)

        if (i + 1) % 50 == 0:
            print(f"  已处理 {i + 1}/{len(symbols)} 只股票... (已验证 {checked} 条)")

    # 登出 baostock
    bs.logout()

    # 4. 汇总统计
    print("\n" + "=" * 80)
    print("验证结果汇总")
    print("=" * 80)

    # 按差异大小分组
    exact_match = [r for r in results if r['diff_pct'] == 0]
    small_diff = [r for r in results if 0 < r['diff_pct'] <= 0.1]
    medium_diff = [r for r in results if 0.1 < r['diff_pct'] <= 1.0]
    large_diff = [r for r in results if r['diff_pct'] > 1.0]

    print(f"\n总共验证: {len(results)} 条记录")
    print(f"  ✅ 完全一致(diff=0): {len(exact_match)} 条 ({len(exact_match)/len(results)*100:.1f}%)")
    print(f"  ✅ 差异极小(0~0.1%): {len(small_diff)} 条 ({len(small_diff)/len(results)*100:.1f}%)")
    print(f"  ⚠️  差异较小(0.1~1%): {len(medium_diff)} 条 ({len(medium_diff)/len(results)*100:.1f}%)")
    print(f"  ❌ 差异较大(>1%): {len(large_diff)} 条 ({len(large_diff)/len(results)*100:.1f}%)")

    if len(errors) > 0:
        print(f"\n⚠️  无法验证(baostock无记录): {len(errors)} 条")

    # 显示差异较大的记录
    if large_diff:
        print("\n" + "=" * 80)
        print(f"❌ 差异>1%的记录 ({len(large_diff)} 条):")
        print("=" * 80)
        for r in large_diff[:20]:  # 最多显示20条
            print(f"  {r['symbol']} | {r['trade_date']} | DB={r['db_factor']:.6f}, bao={r['bao_factor']:.6f}, diff={r['diff_pct']:.3f}%")

    # 最终结论
    print("\n" + "=" * 80)
    print("结论")
    print("=" * 80)

    if len(large_diff) == 0:
        print("\n✅ 所有抽检记录与baostock一致，数据准确性良好。")
        print(f"   - 完全一致: {len(exact_match)} 条")
        print(f"   - 差异<0.1%: {len(small_diff)} 条")
        print(f"   - 差异0.1~1%: {len(medium_diff)} 条")
    else:
        accurate_rate = (len(results) - len(large_diff)) / len(results) * 100
        print(f"\n⚠️  发现 {len(large_diff)} 条记录差异>1%，数据准确率: {accurate_rate:.1f}%")
        print(f"   如需修复差异>1%的记录，请运行: python tests/validate_adjust_factor_batch.py fix")

    print()


if __name__ == "__main__":
    main()