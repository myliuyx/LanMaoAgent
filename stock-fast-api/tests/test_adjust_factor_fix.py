"""
验证并修复 dwd_stock_adjust_factor 表中的异常复权因子。

adj_factor 异常标准: < 0.1 或 > 1.5

adj_factor 的含义: 复权因子 = 除权前收盘价 / 除权后收盘价
- adj_factor < 1 表示除权后股价下跌(分红/送股)
- adj_factor > 1 表示除权后股价上涨(不太可能，正常应该是 < 1)

adj_factor < 0.1 意味着复权后价格是原来的 10 倍以上，这几乎不可能是正常分红/送股，
可能是以下原因:
1. 数据源问题(原始价格错误)
2. 复权因子计算错误
3. 事件日期错误

验证方法:
1. 用 baostock 查询正确的 foreAdjustFactor
2. 对比数据库中的 adj_factor 与 baostock 的值
3. 如果差异 > 1%，标记为需要修复

用法:
    python test_adjust_factor_fix.py        # 只验证不修复
    python test_adjust_factor_fix.py fix    # 验证后确认修复
"""

import sys
sys.path.insert(0, '/home/huajuan/Github_Code/stock-fast-api')

from sqlalchemy import create_engine, text
import baostock as bs
import pandas as pd
from datetime import datetime

DB_URL = "postgresql+psycopg2://postgres:H7k9P2mX5wR1@192.168.3.16:5432/stock_cache_system"

# baostock 前缀映射
BAO_PREFIX = {
    '002131.SZ': 'sz.002131', '002709.SZ': 'sz.002709',
    '300432.SZ': 'sz.300432', '300450.SZ': 'sz.300450',
    '300459.SZ': 'sz.300459', '300628.SZ': 'sz.300628',
    '300738.SZ': 'sz.300738', '603871.SH': 'sh.603871',
}


def get_engine():
    return create_engine(DB_URL)


def get_problematic_records(engine) -> list[dict]:
    """获取所有异常的复权因子记录"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT symbol, trade_date, adj_factor, forward_adj_close, backward_adj_close, event_type
            FROM dwd_stock_adjust_factor
            WHERE adj_factor < 0.1 OR adj_factor > 1.5
            ORDER BY symbol, trade_date
        """))
        return [dict(row._mapping) for row in result.fetchall()]


def validate_with_baostock(symbol: str, trade_date, db_factor: float) -> dict:
    """
    用 baostock 验证单条记录。

    返回:
        {'valid': bool, 'bao_factor': float, 'diff_pct': float, 'needs_fix': bool}
    """
    bao_code = BAO_PREFIX.get(symbol)
    if not bao_code:
        return {'valid': False, 'error': 'unknown symbol'}

    td_str = str(trade_date) if not isinstance(trade_date, str) else trade_date
    year = int(td_str[:4])
    month = int(td_str[5:7])

    # 查询事件日期所在月份的数据
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

    bao_rec = df[df['dividOperateDate'] == td_str]

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


def validate_all_records(engine) -> list[dict]:
    """验证所有异常记录（使用 baostock）"""
    problematic = get_problematic_records(engine)

    results = []
    for rec in problematic:
        symbol = rec['symbol']
        td = rec['trade_date']
        td_str = td.strftime('%Y-%m-%d') if hasattr(td, 'strftime') else str(td)
        db_factor = float(rec['adj_factor'])

        result = validate_with_baostock(symbol, td, db_factor)

        results.append({
            'symbol': symbol,
            'trade_date': td_str,
            'db_factor': db_factor,
            'event_type': rec['event_type'],
            **result,
        })

    return results


def fix_record(engine, symbol: str, trade_date: str, new_factor: float) -> bool:
    """修复单条记录"""
    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE dwd_stock_adjust_factor
            SET adj_factor = :new_factor
            WHERE symbol = :symbol AND trade_date = :trade_date
        """), {
            'new_factor': new_factor,
            'symbol': symbol,
            'trade_date': trade_date,
        })
        return result.rowcount > 0


def main():
    engine = get_engine()
    do_fix = len(sys.argv) > 1 and sys.argv[1] == 'fix'

    print("=" * 80)
    print("dwd_stock_adjust_factor 异常复权因子验证与修复")
    print("=" * 80)

    # 登录 baostock
    lg = bs.login()
    print(f"\nbaostock 登录: {lg.error_code} {lg.error_msg}")

    # 验证所有记录
    results = validate_all_records(engine)

    # 登出 baostock
    bs.logout()

    # 打印结果
    print("\n" + "=" * 80)
    print("验证结果 (baostock foreAdjustFactor vs DB adj_factor)")
    print("=" * 80)

    need_fix = []
    for r in results:
        if r.get('error'):
            status = f"⚠️ 跳过({r['error']})"
        elif r['needs_fix']:
            status = f"❌ 需修复"
            need_fix.append(r)
        else:
            status = f"✅ 正常"
            if r['diff_pct'] > 0.01:
                status += f"(差{r['diff_pct']:.3f}%)"

        print(f"\n{status}: {r['symbol']} | {r['trade_date']}")
        print(f"  DB值: {r['db_factor']:.6f}")
        if r.get('bao_factor'):
            print(f"  正确值(baostock): {r['bao_factor']:.6f}")
            print(f"  差异: {r['diff_pct']:.3f}%")
        print(f"  事件: {r['event_type']}")

    # 汇总
    to_fix = [r for r in results if r.get('needs_fix') and r.get('bao_factor')]
    ok = [r for r in results if not r.get('needs_fix') and r.get('valid')]

    print("\n" + "=" * 80)
    print(f"汇总: {len(to_fix)} 条需修复, {len(ok)} 条正常, {len(results) - len(to_fix) - len(ok)} 条跳过")
    print("=" * 80)

    if not to_fix:
        print("\n✅ 所有异常记录已验证，数据正确，无需修复。")
        return

    if not do_fix:
        print("\n如需执行修复，请运行: python test_adjust_factor_fix.py fix")
        return

    # 执行修复
    print("\n待修复记录:")
    for r in to_fix:
        print(f"  {r['symbol']} | {r['trade_date']} | {r['db_factor']:.6f} → {r['bao_factor']:.6f}")

    confirm = input(f"\n确认修复以上 {len(to_fix)} 条记录? (yes/no): ")
    if confirm.lower() != 'yes':
        print("已取消修复。")
        return

    success = 0
    for r in to_fix:
        if fix_record(engine, r['symbol'], r['trade_date'], r['bao_factor']):
            print(f"✅ 已修复: {r['symbol']} | {r['trade_date']} | {r['bao_factor']:.6f}")
            success += 1
        else:
            print(f"❌ 修复失败: {r['symbol']} | {r['trade_date']}")

    print(f"\n修复完成: {success}/{len(to_fix)} 条成功。")


if __name__ == "__main__":
    main()