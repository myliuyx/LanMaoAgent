"""Board sync service - 板块数据同步服务

从 efinance 获取股票所属板块，过滤噪音，写入 DB。
"""
import re
from datetime import date
from typing import Any

import efinance as ef
from sqlalchemy.orm import Session

from app.repositories.board_sync_repository import BoardSyncRepository


# 需要过滤掉的板块名模式（支持正则）
_EXCLUDE_NAME_PATTERNS = [
    # 交易通道类（注意：正则 [xxx] 是字符类，不是 "或"，这里用分组）
    r"融资融券", r"转融通", r"沪股通", r"深股通", r"陆股通",
    # 指数成分类（后缀 _ 是东方财经常加的噪声）
    r"上证50", r"上证180", r"深证100", r"沪深300", r"HS300",
    r"富时罗素", r"标准普尔", r"MSCI", r"证金持股",
    # 风格/主题标签
    r"百元股", r"大盘股", r"大盘成长", r"大盘价值", r"权重股",
    r"茅指数", r"宁组合", r"央国企改革", r"破净股", r"长期破净",
    r"周期股", r"红利股", r"IPO受益",
    # 跨市场标签
    r"^AH股",
]

# 板块名 → board_type 推断规则（按顺序匹配，第一个命中的为准）
_BOARD_TYPE_RULES: list[tuple[str, str]] = [
    # INDUSTRY: 明确行业名
    (r"银行", "INDUSTRY"),
    (r"白酒", "INDUSTRY"),
    (r"食品饮料", "INDUSTRY"),
    (r"医药", "INDUSTRY"),
    (r"医疗", "INDUSTRY"),
    (r"电子[^\w]", "INDUSTRY"),
    (r"软件", "INDUSTRY"),
    (r"计算机", "INDUSTRY"),
    (r"电池|锂电", "INDUSTRY"),
    (r"半导体", "INDUSTRY"),
    (r"新能源[车]?", "INDUSTRY"),
    (r"光伏", "INDUSTRY"),
    (r"通信", "INDUSTRY"),
    (r"传媒", "INDUSTRY"),
    (r"房地产", "INDUSTRY"),
    (r"建筑", "INDUSTRY"),
    (r"汽车", "INDUSTRY"),
    (r"机械设备", "INDUSTRY"),
    (r"化工", "INDUSTRY"),
    (r"有色金属", "INDUSTRY"),
    (r"煤炭", "INDUSTRY"),
    (r"钢铁", "INDUSTRY"),
    (r"电力设备", "INDUSTRY"),
    (r"军工", "INDUSTRY"),
    (r"农业", "INDUSTRY"),
    (r"零售", "INDUSTRY"),
    (r"旅游", "INDUSTRY"),
    (r"教育", "INDUSTRY"),
    (r"金融", "INDUSTRY"),
    (r"保险", "INDUSTRY"),
    (r"证券", "INDUSTRY"),
    (r"集成电路", "INDUSTRY"),
    (r"存储芯片", "INDUSTRY"),
    (r"国产芯片", "INDUSTRY"),
    (r"芯片设计", "INDUSTRY"),
    # CONCEPT: 概念/主题
    (r"概念", "CONCEPT"),
    (r"主题", "CONCEPT"),
    (r"AI", "CONCEPT"),
    (r"人工智能", "CONCEPT"),
    (r"云计算", "CONCEPT"),
    (r"大数据", "CONCEPT"),
    (r"物联网", "CONCEPT"),
    (r"5G", "CONCEPT"),
    (r"机器人", "CONCEPT"),
    (r"智能[驾驶家居穿戴]", "CONCEPT"),
    (r"新能源车", "CONCEPT"),
    (r"储能", "CONCEPT"),
    (r"固态电池", "CONCEPT"),
    (r"钠离子电池", "CONCEPT"),
    (r"液冷", "CONCEPT"),
    (r" CPO", "CONCEPT"),
    (r"铜缆高速", "CONCEPT"),
    (r"光通信", "CONCEPT"),
    (r"数据中心", "CONCEPT"),
    (r"虚拟现实", "CONCEPT"),
    (r"混合现实", "CONCEPT"),
    (r"消费电子", "CONCEPT"),
    (r"苹果概念", "CONCEPT"),
    (r"华为概念", "CONCEPT"),
    (r"小米汽车", "CONCEPT"),
    (r"特斯拉概念", "CONCEPT"),
    (r"宁德时代", "CONCEPT"),
    (r"宁组合", "CONCEPT"),
    (r"茅组合", "CONCEPT"),
    (r"医美", "CONCEPT"),
    (r"养老", "CONCEPT"),
    (r"互联医疗", "CONCEPT"),
    (r"跨境支付", "CONCEPT"),
    (r"数字货币", "CONCEPT"),
    (r"区块链", "CONCEPT"),
    (r"信创", "CONCEPT"),
    (r"Kimi", "CONCEPT"),
    # AREA: 地区
    (r"板块$", "AREA"),  # 如 "贵州板块", "广东板块"
    (r"特区", "AREA"),
    (r"成渝", "AREA"),
]


def _is_excluded(name: str) -> bool:
    for pattern in _EXCLUDE_NAME_PATTERNS:
        if re.search(pattern, name):
            return True
    return False


def _infer_board_type(name: str) -> str | None:
    for pattern, btype in _BOARD_TYPE_RULES:
        if re.search(pattern, name):
            return btype
    return "OTHER"


def _normalize_efinance_boards(raw_df) -> list[dict[str, Any]]:
    """把 efinance 返回的 DataFrame 标准化为 dict 列表。"""
    import pandas as pd

    if raw_df is None or raw_df.empty:
        return []

    # 识别列名
    name_col = next(
        (
            col
            for col in raw_df.columns
            if str(col) in {"板块名称", "板块", "所属板块", "板块名", "name", "industry"}
        ),
        None,
    )
    code_col = next(
        (
            col
            for col in raw_df.columns
            if str(col) in {"板块代码", "代码", "code"}
        ),
        None,
    )

    if name_col is None:
        # fallback: 逐行迭代
        results = []
        dedupe = set()
        for _, row in raw_df.iterrows():
            name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None
            if name and name not in dedupe:
                dedupe.add(name)
                results.append({"name": name, "code": None, "type": None})
        return results

    results = []
    dedupe = set()
    for _, row in raw_df.iterrows():
        name_raw = row.get(name_col, "")
        if pd.isna(name_raw) or not str(name_raw).strip():
            continue
        name = str(name_raw).strip()
        if name in dedupe:
            continue
        dedupe.add(name)
        code = str(row.get(code_col)).strip() if code_col and not pd.isna(row.get(code_col)) else None
        board_type = _infer_board_type(name) if not _is_excluded(name) else None
        results.append({"name": name, "code": code, "type": board_type})

    return results


class BoardSyncService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BoardSyncRepository(db)

    def sync_stock(self, symbol: str, trade_date: date | None = None) -> dict[str, Any]:
        """
        同步单只股票的板块数据。

        1. 从 efinance 获取原始板块列表
        2. 过滤噪音 + 推断 board_type
        3. 写入 dwd_board_master + dwd_board_relation（原子操作）
        4. 返回统计信息
        """
        if trade_date is None:
            trade_date = date.today()

        # 去掉 .SH / .SZ 后缀，efinance 不支持带后缀格式
        clean_symbol = symbol.split(".")[0]

        # 获取 efinance 原始数据
        try:
            raw_df = ef.stock.get_belong_board(clean_symbol)
        except Exception as e:
            return {"success": False, "symbol": symbol, "error": str(e), "boards_synced": 0}

        # 标准化 + 过滤
        boards = _normalize_efinance_boards(raw_df)
        filtered = [b for b in boards if not _is_excluded(b["name"])]

        # 使用事务确保原子性：master 和 relation 要么同时成功，要么同时回滚
        try:
            with self.db.begin():
                # 写入板块主表
                for b in filtered:
                    self.repo.upsert_board_master(
                        board_code=b["code"],
                        board_name=b["name"],
                        board_type=b["type"],
                    )

                # 写入板块关系表（全量替换，无 trade_date 维度）
                self.repo.batch_upsert_relations(
                    symbol=symbol,
                    boards=[
                        {"board_code": b["code"], "board_type": b["type"]}
                        for b in filtered
                        if b["code"]
                    ],
                )
        except Exception as e:
            self.db.rollback()
            return {"success": False, "symbol": symbol, "error": f"数据库写入失败: {e}", "boards_synced": 0}

        return {
            "success": True,
            "symbol": symbol,
            "trade_date": str(trade_date),
            "raw_count": len(boards),
            "filtered_count": len(filtered),
            "boards_synced": len([b for b in filtered if b["code"]]),
            "boards": filtered,
        }

    def batch_sync(self, symbols: list[str], trade_date: date | None = None) -> list[dict[str, Any]]:
        """批量同步多只股票的板块数据。"""
        if trade_date is None:
            trade_date = date.today()

        results = []
        for symbol in symbols:
            result = self.sync_stock(symbol, trade_date)
            results.append(result)
            # 防止频率过快，简单 delay
            import time
            time.sleep(0.2)

        return results
