from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.utils.safe_float import _safe_float


# 策略元信息注册表
STRATEGY_METADATA = {
    "bottom_volume": {
        "id": "bottom_volume",
        "name": "底部放量",
        "name_en": "Bottom Volume",
        "description": "持续下跌后出现放量阳线，量比>3倍，确认底部信号",
        "priority": 60,
        "market_state": "trending_down",
        "signals": ["量比>3", "持续下跌20日", "阳线确认", "下影线支撑"],
    },
    "box_oscillation": {
        "id": "box_oscillation",
        "name": "箱体震荡",
        "name_en": "Box Oscillation",
        "description": "价格在高低价之间震荡，箱体宽度>5%，适用于横盘整理行情",
        "priority": 50,
        "market_state": "sideways",
        "signals": ["箱体宽度>5%", "多次触碰高/低点", "量能稳定"],
    },
    "bull_trend": {
        "id": "bull_trend",
        "name": "多头趋势",
        "name_en": "Bull Trend",
        "description": "默认策略。MA5≥MA10≥MA20多头排列，MA20斜率向上，趋势评分高",
        "priority": 10,
        "market_state": "trending_up",
        "signals": ["MA多头排列", "MA20斜率向上", "趋势评分>60"],
    },
    "chan_theory": {
        "id": "chan_theory",
        "name": "缠论",
        "name_en": "Chan Theory",
        "description": "基于缠论中枢结构，识别买卖点（1/2/3买/卖），MACD背驰判断",
        "priority": 70,
        "market_state": "volatile",
        "signals": ["分型结构", "笔/线段", "中枢识别", "MACD背驰"],
    },
    "ma_golden_cross": {
        "id": "ma_golden_cross",
        "name": "均线金叉",
        "name_en": "MA Golden Cross",
        "description": "MA5上穿MA10，金叉发生在近3日内，量比>1.2辅助确认",
        "priority": 20,
        "market_state": "trending_up",
        "signals": ["MA5上穿MA10", "近3日内金叉", "量比>1.2", "乖离率<5%"],
    },
    "one_yang_three_yin": {
        "id": "one_yang_three_yin",
        "name": "一阳夹三阴",
        "name_en": "One Yang Three Yin",
        "description": "第1日大阳、第2-4日三阴不破第1日开盘、第5日阳线，缩量整理",
        "priority": 110,
        "market_state": "通用",
        "signals": ["第1日大阳线", "第2-4日三阴", "不破第一日开盘", "第5日阳线确认"],
    },
    "shrink_pullback": {
        "id": "shrink_pullback",
        "name": "缩量回踩",
        "name_en": "Shrink Pullback",
        "description": "上升趋势中价格回踩MA5或MA10，成交量萎缩至5日均量70%以下",
        "priority": 40,
        "market_state": "trending_down/sideways",
        "signals": ["MA5>MA10>MA20", "回踩MA5/MA10", "缩量<70%", "乖离率<2%"],
    },
    "volume_breakout": {
        "id": "volume_breakout",
        "name": "放量突破",
        "name_en": "Volume Breakout",
        "description": "价格放量突破阻力位（20日高点或震荡平台），量比>2，收盘站上阻力位",
        "priority": 30,
        "market_state": "trending_up",
        "signals": ["突破20日高点", "量比>2", "收盘站上阻力位", "乖离率<5%"],
    },
    "wave_theory": {
        "id": "wave_theory",
        "name": "波浪理论",
        "name_en": "Wave Theory",
        "description": "识别5浪推动和3浪调整结构，斐波那契回撤位判断，MACD顶背离确认",
        "priority": 80,
        "market_state": "volatile",
        "signals": ["5浪推动识别", "3浪调整结构", "斐波那契回撤", "MACD顶背离"],
    },
}


class StrategyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_stocks_latest(self, trade_date: str) -> list[dict]:
        """获取指定交易日全部股票的最新日线+因子数据"""
        sql = text("""
            SELECT
                m.symbol, m.name, m.exchange,
                d.close, d.change_pct, d.turnover_rate_f as turnover_rate,
                d.volume, d.amplitude,
                f.ma5, f.ma10, f.ma20, f.ma60, f.ma120,
                f.volume_ma5, f.volume_ma10,
                f.macd_dif, f.macd_dea, f.macd_hist,
                f.high_20, f.high_60, f.low_20, f.low_60,
                f.pct_5d, f.pct_10d, f.pct_20d, f.pct_60d,
                f.rsi_6, f.rsi_14, f.trend_score,
                f.is_new_high_60d, f.is_break_ma20,
                d.volume_ratio
            FROM dwd_security_master m
            LEFT JOIN dwd_stock_daily d ON d.symbol = m.symbol
                AND d.trade_date = :trade_date
            LEFT JOIN dwd_stock_factor_daily f ON f.symbol = m.symbol
                AND f.trade_date = :trade_date
            WHERE m.status = 'LISTED'
        """)
        result = self.db.execute(sql, {"trade_date": trade_date})
        rows = result.mappings().fetchall()
        float_fields = (
            "close", "change_pct", "turnover_rate", "volume", "amplitude",
            "ma5", "ma10", "ma20", "ma60", "ma120",
            "volume_ma5", "volume_ma10",
            "macd_dif", "macd_dea", "macd_hist",
            "high_20", "high_60", "low_20", "low_60",
            "pct_5d", "pct_10d", "pct_20d", "pct_60d",
            "rsi_6", "rsi_14", "trend_score", "volume_ratio",
        )
        return [
            {k: (_safe_float(v) if k in float_fields and v is not None else v) for k, v in row.items()}
            for row in rows
        ]

    def get_daily_history(self, symbol: str, trade_date: str, days: int = 120) -> list[dict]:
        """获取指定股票历史日线数据（按日期升序）"""
        sql = text("""
            SELECT trade_date, open, high, low, close, volume,
                   turnover_rate_f as turnover_rate
            FROM dwd_stock_daily
            WHERE symbol = :symbol AND trade_date <= :trade_date
            ORDER BY trade_date DESC
            LIMIT :days
        """)
        result = self.db.execute(sql, {"symbol": symbol, "trade_date": trade_date, "days": days})
        rows = result.mappings().fetchall()
        # Decimal → float 转换，避免算术运算报错
        float_fields = ("open", "high", "low", "close", "volume", "turnover_rate")
        return [
            {k: (_safe_float(v) if k in float_fields and v is not None else v) for k, v in row.items()}
            for row in reversed(rows)
        ]

    def get_factor_history(self, symbol: str, trade_date: str, days: int = 120) -> list[dict]:
        """获取指定股票历史技术因子数据（按日期降序）"""
        sql = text("""
            SELECT trade_date, ma5, ma10, ma20, ma60, ma120,
                   macd_dif, macd_dea, macd_hist,
                   volume_ma5, volume_ma10,
                   high_20, high_60, low_20, low_60,
                   pct_5d, pct_10d, pct_20d, pct_60d, trend_score
            FROM dwd_stock_factor_daily
            WHERE symbol = :symbol AND trade_date <= :trade_date
            ORDER BY trade_date DESC
            LIMIT :days
        """)
        result = self.db.execute(sql, {"symbol": symbol, "trade_date": trade_date, "days": days})
        rows = result.mappings().fetchall()
        float_fields = ("ma5", "ma10", "ma20", "ma60", "ma120",
                        "macd_dif", "macd_dea", "macd_hist",
                        "volume_ma5", "volume_ma10",
                        "high_20", "high_60", "low_20", "low_60",
                        "pct_5d", "pct_10d", "pct_20d", "pct_60d", "trend_score")
        return [
            {k: (_safe_float(v) if k in float_fields and v is not None else v) for k, v in row.items()}
            for row in rows
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # 策略计算方法
    # ─────────────────────────────────────────────────────────────────────────────

    def calc_bottom_volume(self, stock: dict, daily_history: list[dict]) -> Optional[dict]:
        """
        底部放量策略：
        1. 20日高点到近期低点跌幅 > 15%
        2. 当日量比 > 3
        3. 收阳线（close > open）
        4. 下影线支撑（low 接近 low_x）
        """
        if len(daily_history) < 20:
            return None

        recent_20 = daily_history[-20:]
        high_20 = max(r["high"] for r in recent_20 if r["high"] is not None)
        low_20 = min(r["low"] for r in recent_20 if r["low"] is not None)

        # 近期低点（最近5日）
        recent_5 = daily_history[-5:]
        low_recent = min(r["low"] for r in recent_5 if r["low"] is not None)

        # 跌幅判断
        if high_20 <= 0 or low_recent >= high_20:
            return None
        drop_pct = (high_20 - low_recent) / high_20 * 100
        if drop_pct <= 15:
            return None

        # 当日数据（history最后一条）
        today = daily_history[-1]
        volume_ratio = _safe_float(today.get("volume_ratio")) or 0
        close = _safe_float(today.get("close")) or 0
        open_price = _safe_float(today.get("open")) or 0

        if volume_ratio <= 3:
            return None
        if close <= open_price:
            return None

        # 下影线：low 低于 close 和 open 的较低者一定比例
        lower_ref = min(close, open_price)
        lower_shadow = lower_ref - (today.get("low") or 0)
        if lower_shadow <= 0:
            return None

        score = min(100, drop_pct * 3 + volume_ratio * 10)
        return {
            "signals": [
                {"name": "20日跌幅", "value": round(drop_pct, 2), "description": f"{round(drop_pct, 1)}%"},
                {"name": "量比", "value": round(volume_ratio, 2), "description": f"{round(volume_ratio, 1)}x"},
                {"name": "K线", "value": "阳线", "description": "收盘>开盘"},
            ],
            "match_reason": f"20日跌幅{round(drop_pct,1)}%，量比{volume_ratio}x，底部放量信号",
            "score": round(score, 1),
        }

    def calc_box_oscillation(self, stock: dict, daily_history: list[dict]) -> Optional[dict]:
        """
        箱体震荡策略：
        1. 120日内价格在高低点之间震荡
        2. 箱体宽度(顶部-底部)/底部 > 5%
        3. 当前价在箱体中部位置
        """
        if len(daily_history) < 30:
            return None

        highs = [r["high"] for r in daily_history[-120:] if r["high"] is not None]
        lows = [r["low"] for r in daily_history[-120:] if r["low"] is not None]
        if not highs or not lows:
            return None

        box_high = max(highs)
        box_low = min(lows)
        if box_low <= 0:
            return None

        box_width = (box_high - box_low) / box_low * 100
        if box_width <= 5:
            return None

        # 当前价格位置
        close = _safe_float(stock.get("close")) or 0
        if close <= 0:
            return None

        # 价格在箱体中的位置（0%=箱底，100%=箱顶）
        position = (close - box_low) / (box_high - box_low) * 100 if box_high != box_low else 50

        # 触碰次数（高价接近箱顶或低价接近箱底）
        touch_high = sum(1 for r in daily_history[-60:] if r.get("high") and box_high > 0 and (box_high - r["high"]) / box_high < 0.03)
        touch_low = sum(1 for r in daily_history[-60:] if r.get("low") and box_low > 0 and (r["low"] - box_low) / box_low < 0.03)

        if touch_high < 2 or touch_low < 2:
            return None

        score = min(100, box_width * 5 + position * 0.5)
        return {
            "signals": [
                {"name": "箱体宽度", "value": round(box_width, 2), "description": f"{round(box_width, 1)}%"},
                {"name": "箱体位置", "value": round(position, 1), "description": f"{round(position, 0)}%"},
                {"name": "高低触碰", "value": f"{touch_high}/{touch_low}", "description": "近60日高低点触碰次数"},
            ],
            "match_reason": f"箱体宽度{round(box_width,1)}%，价格位于{round(position,0)}%分位",
            "score": round(score, 1),
        }

    def calc_bull_trend(self, stock: dict, daily_history: list[dict]) -> Optional[dict]:
        """
        默认多头趋势策略：
        1. MA5 >= MA10 >= MA20（多头排列）
        2. MA20 斜率向上（当前MA20 > 10日前MA20）
        3. 趋势评分 >= 60
        """
        ma5 = _safe_float(stock.get("ma5"))
        ma10 = _safe_float(stock.get("ma10"))
        ma20 = _safe_float(stock.get("ma20"))
        trend_score = _safe_float(stock.get("trend_score")) or 0

        if not all([ma5, ma10, ma20]):
            return None

        if not (ma5 >= ma10 >= ma20):
            return None

        if trend_score < 60:
            return None

        # MA20斜率：需要10日前的MA20
        factor_history = self.get_factor_history(stock["symbol"], str(daily_history[-1]["trade_date"]) if daily_history else "", days=20)
        if len(factor_history) >= 10:
            ma20_10d_ago = _safe_float(factor_history[9].get("ma20"))
            if ma20_10d_ago and ma20 <= ma20_10d_ago:
                return None
        else:
            return None

        # 突破量能确认
        volume_ratio = _safe_float(stock.get("volume_ratio")) or 1
        change_pct = abs(_safe_float(stock.get("change_pct")) or 0)

        score = min(100, trend_score + volume_ratio * 5 + change_pct * 2)
        return {
            "signals": [
                {"name": "均线多头", "value": "是", "description": f"MA5({round(ma5,2)})≥MA10({round(ma10,2)})≥MA20({round(ma20,2)})"},
                {"name": "MA20斜率", "value": "向上", "description": "10日内MA20上升"},
                {"name": "趋势评分", "value": round(trend_score, 1), "description": f"{trend_score}"},
            ],
            "match_reason": f"均线多头排列，趋势评分{trend_score}，上升趋势确认",
            "score": round(score, 1),
        }

    def calc_ma_golden_cross(self, stock: dict, daily_history: list[dict]) -> Optional[dict]:
        """
        均线金叉策略：
        1. MA5 上穿 MA10（金叉发生在近3日内）
        2. MACD 零轴上方金叉或当前 DIF>DEA
        3. 金叉日量比 > 1.2
        4. 价格乖离率 < 5%
        """
        factor_history = self.get_factor_history(stock["symbol"], str(daily_history[-1]["trade_date"]) if daily_history else "", days=10)
        if len(factor_history) < 3:
            return None

        # 获取近3日MA数据
        ma_series = []
        for row in factor_history[:5]:
            ma5 = _safe_float(row.get("ma5"))
            ma10 = _safe_float(row.get("ma10"))
            if ma5 is not None and ma10 is not None:
                ma_series.append({"ma5": ma5, "ma10": ma10})

        if len(ma_series) < 3:
            return None

        # 检查金叉：前一天 MA5 <= MA10，当天 MA5 > MA10
        golden_cross_found = False
        golden_cross_day = -1
        for i in range(1, min(3, len(ma_series))):
            if ma_series[i]["ma5"] > ma_series[i]["ma10"] and ma_series[i - 1]["ma5"] <= ma_series[i - 1]["ma10"]:
                golden_cross_found = True
                golden_cross_day = i
                break

        if not golden_cross_found:
            return None

        # MACD 状态
        macd_dif = _safe_float(stock.get("macd_dif")) or 0
        macd_dea = _safe_float(stock.get("macd_dea")) or 0
        macd_bullish = macd_dif > macd_dea or macd_dif > 0

        # 金叉日量比
        volume_ratio = _safe_float(stock.get("volume_ratio")) or 0
        if volume_ratio <= 1.2:
            return None

        # 乖离率
        ma20 = _safe_float(stock.get("ma20"))
        close = _safe_float(stock.get("close")) or 0
        if ma20 and ma20 > 0:
            bias = abs(close - ma20) / ma20 * 100
            if bias >= 5:
                return None

        score = min(100, 60 + volume_ratio * 10 + (20 if macd_bullish else 0))
        return {
            "signals": [
                {"name": "金叉", "value": "MA5上穿MA10", "description": f"近{golden_cross_day + 1}日内金叉"},
                {"name": "量比", "value": round(volume_ratio, 2), "description": f"{round(volume_ratio, 1)}x"},
                {"name": "MACD", "value": "多头" if macd_bullish else "空头", "description": f"DIF{round(macd_dif,3)} DEA{round(macd_dea, 3)}"},
            ],
            "match_reason": f"均线金叉发生在近{golden_cross_day + 1}日内，量比{volume_ratio}x",
            "score": round(score, 1),
        }

    def calc_one_yang_three_yin(self, stock: dict, daily_history: list[dict]) -> Optional[dict]:
        """
        一阳夹三阴策略：
        1. 第1日（大阳线，实体>2%）
        2. 第2-4日（三阴，不破第1日开盘价）
        3. 第5日（阳线确认）
        4. 成交量逐步萎缩（量比<0.8）
        """
        if len(daily_history) < 5:
            return None

        days = daily_history[-5:]
        d1, d2, d3, d4, d5 = days[0], days[1], days[2], days[3], days[4]

        # 第1日：大阳线（close > open * 1.02）
        open1 = _safe_float(d1.get("open")) or 0
        close1 = _safe_float(d1.get("close")) or 0
        if open1 <= 0 or close1 <= open1 * 1.02:
            return None

        # 第2-4日：三阴，close < open，且不破第1日开盘
        for d in [d2, d3, d4]:
            open_d = _safe_float(d.get("open")) or 0
            close_d = _safe_float(d.get("close")) or 0
            if close_d >= open_d or close_d < open1:
                return None

        # 第5日：阳线
        open5 = _safe_float(d5.get("open")) or 0
        close5 = _safe_float(d5.get("close")) or 0
        if close5 <= open5:
            return None

        # 缩量：第2-4日量比逐步下降
        vol2 = _safe_float(d2.get("volume_ratio")) or 1
        vol3 = _safe_float(d3.get("volume_ratio")) or 1
        vol4 = _safe_float(d4.get("volume_ratio")) or 1
        if not (vol2 < 0.8 or vol3 < 0.8 or vol4 < 0.8):
            return None

        # 均线多头背景
        ma5 = _safe_float(stock.get("ma5")) or 0
        ma10 = _safe_float(stock.get("ma10")) or 0
        ma20 = _safe_float(stock.get("ma20")) or 0
        ma_bullish = ma5 >= ma10 >= ma20

        score = 85 + (10 if ma_bullish else 0)
        return {
            "signals": [
                {"name": "第1日阳线", "value": f"+{round((close1/open1-1)*100, 1)}%", "description": "大阳线确认"},
                {"name": "三阴整理", "value": "未破第1日开盘", "description": "缩量整理"},
                {"name": "第5日阳线", "value": "确认信号", "description": "阳线收盘"},
                {"name": "均线背景", "value": "多头" if ma_bullish else "空头", "description": "MA排列"},
            ],
            "match_reason": "一阳夹三阴形态，缩量整理后阳线确认",
            "score": round(score, 1),
        }

    def calc_shrink_pullback(self, stock: dict, daily_history: list[dict]) -> Optional[dict]:
        """
        缩量回踩策略：
        1. MA5 > MA10 > MA20（多头排列）
        2. 价格回踩 MA5（误差1%）或 MA10（误差2%）
        3. 成交量 < 5日均量70%
        4. MA5乖离率 < 2%
        """
        ma5 = _safe_float(stock.get("ma5")) or 0
        ma10 = _safe_float(stock.get("ma10")) or 0
        ma20 = _safe_float(stock.get("ma20")) or 0
        close = _safe_float(stock.get("close")) or 0

        if not all([ma5, ma10, ma20]) or not (ma5 >= ma10 >= ma20):
            return None

        if close <= 0:
            return None

        # 价格回踩判断
        pullback_ma5 = abs(close - ma5) / ma5 * 100 <= 1
        pullback_ma10 = abs(close - ma10) / ma10 * 100 <= 2
        if not (pullback_ma5 or pullback_ma10):
            return None

        # 缩量
        volume_ratio = _safe_float(stock.get("volume_ratio")) or 1
        if volume_ratio >= 0.7:
            return None

        # MA5乖离率
        bias_ma5 = abs(close - ma5) / ma5 * 100
        if bias_ma5 >= 2:
            return None

        score = min(100, 70 + (20 if pullback_ma5 else 10) + (10 if volume_ratio < 0.5 else 0))
        return {
            "signals": [
                {"name": "回踩位置", "value": f"MA5" if pullback_ma5 else "MA10", "description": f"回踩{round(bias_ma5, 2)}%"},
                {"name": "缩量", "value": round(volume_ratio, 2), "description": f"仅为5日均量{round(volume_ratio * 100, 0)}%"},
                {"name": "乖离率", "value": round(bias_ma5, 2), "description": f"MA5乖离{round(bias_ma5, 2)}%"},
            ],
            "match_reason": f"回踩MA{5 if pullback_ma5 else 10}企稳，缩量{round(volume_ratio * 100)}%",
            "score": round(score, 1),
        }

    def calc_volume_breakout(self, stock: dict, daily_history: list[dict]) -> Optional[dict]:
        """
        放量突破策略：
        1. 阻力位识别（20日高点或前期震荡平台顶部）
        2. 量比 > 2
        3. 收盘站上阻力位
        4. 乖离率 < 5%
        """
        if len(daily_history) < 20:
            return None

        recent_20 = daily_history[-20:]
        high_20 = max(r["high"] for r in recent_20 if r["high"] is not None)
        close = _safe_float(stock.get("close")) or 0

        if high_20 <= 0 or close <= 0:
            return None

        # 收盘在阻力位上方
        if close < high_20:
            return None

        # 放量
        volume_ratio = _safe_float(stock.get("volume_ratio")) or 0
        if volume_ratio <= 2:
            return None

        # 乖离率
        ma5 = _safe_float(stock.get("ma5")) or 0
        if ma5 > 0:
            bias = (close - ma5) / ma5 * 100
            if bias >= 5:
                return None

        # 强势收盘（收盘在当日振幅上方30%）
        today = daily_history[-1]
        day_high = today.get("high") or 0
        day_low = today.get("low") or 0
        amplitude = day_high - day_low
        if amplitude > 0:
            close_position = (close - day_low) / amplitude * 100
            if close_position < 30:
                return None

        score = min(100, 60 + volume_ratio * 10 + close_position * 0.5)
        return {
            "signals": [
                {"name": "阻力突破", "value": round(high_20, 2), "description": f"突破20日高点{round(high_20, 2)}"},
                {"name": "量比", "value": round(volume_ratio, 2), "description": f"{round(volume_ratio, 1)}x放量"},
                {"name": "收盘位置", "value": round(close_position, 1), "description": f"当日振幅{round(close_position, 0)}%分位"},
            ],
            "match_reason": f"放量突破20日高点{high_20}，量比{volume_ratio}x",
            "score": round(score, 1),
        }

    def calc_wave_theory(self, stock: dict, daily_history: list[dict]) -> Optional[dict]:
        """
        波浪理论策略（简化版）：
        1. 120日数据识别高低点
        2. 基于MACD识别推动浪和调整浪
        3. 斐波那契回撤位判断（38.2%~61.8%）
        4. MACD顶背离确认第5浪
        """
        if len(daily_history) < 60:
            return None

        factor_history = self.get_factor_history(stock["symbol"], str(daily_history[-1]["trade_date"]) if daily_history else "", days=120)
        if len(factor_history) < 20:
            return None

        # 识别最近的高低点序列
        prices = [(r["trade_date"], r["high"], r["low"]) for r in daily_history[-60:] if r.get("high") and r.get("low")]
        if len(prices) < 20:
            return None

        # 计算波动结构
        highs = [p[1] for p in prices]
        lows = [p[2] for p in prices]

        # 简化：找最近的高点和低点
        recent_high = max(highs[-20:])
        recent_low = min(lows[-20:])

        if recent_low <= 0 or recent_high <= recent_low:
            return None

        # 斐波那契回撤判断
        wave_range = recent_high - recent_low
        fib_382 = recent_low + wave_range * 0.382
        fib_618 = recent_low + wave_range * 0.618

        close = _safe_float(stock.get("close")) or 0
        if close < fib_382 or close > recent_high:
            return None

        # MACD 顶背离判断
        macd_dif = _safe_float(stock.get("macd_dif")) or 0
        macd_hist = _safe_float(stock.get("macd_hist")) or 0

        # 近10日MACD是否出现顶背离（价格创新高但MACD未创新高）
        recent_10_factors = factor_history[:10]
        macd_values = [(r["macd_dif"], r["macd_hist"]) for r in recent_10_factors if r.get("macd_dif") is not None]
        if len(macd_values) >= 5:
            max_dif_5d_ago = max(v[0] for v in macd_values[5:])
            current_dif = macd_values[0][0] if macd_values else 0
            # 价格创20日新高但MACD未创新高 → 顶背离
            is_divergence = close >= recent_high and current_dif < max_dif_5d_ago
        else:
            is_divergence = False

        # 当前在调整浪中（价格在斐波那契回撤位）
        in_correction = fib_382 <= close <= fib_618

        if not in_correction:
            return None

        score = 75 + (15 if is_divergence else 0)
        return {
            "signals": [
                {"name": "斐波回撤", "value": f"{round((close - recent_low) / wave_range * 100, 1)}%", "description": f"回撤至{round(close, 2)}，斐波那契{round((close - recent_low) / wave_range * 100, 0)}%位"},
                {"name": "MACD背离", "value": "是" if is_divergence else "否", "description": "顶背离确认"},
                {"name": "波浪位置", "value": "调整浪中", "description": "价格在回调浪中"},
            ],
            "match_reason": f"处于斐波那契回调位(38.2%~61.8%)，价格{round(close, 2)}",
            "score": round(score, 1),
        }

    def calc_chan_theory(self, stock: dict, daily_history: list[dict]) -> Optional[dict]:
        """
        缠论策略（简化版）：
        1. 分型识别（顶分型/底分型）
        2. 笔的确认（5根不重叠的K线）
        3. 中枢结构识别
        4. MACD背驰判断
        """
        if len(daily_history) < 30:
            return None

        macd_dif = _safe_float(stock.get("macd_dif")) or 0
        macd_dea = _safe_float(stock.get("macd_dea")) or 0
        macd_hist = _safe_float(stock.get("macd_hist")) or 0

        # 检查是否有买卖点信号
        # 底背离：DIF和价格创新低，但MACD未创新低
        close = _safe_float(stock.get("close")) or 0

        # 简化逻辑：检查最近5日的分型结构
        recent_5 = daily_history[-5:]
        if len(recent_5) < 5:
            return None

        # 检查是否有底分型（中间K线高点最低，两侧高点较高）
        # 或顶分型（中间K线低点最高，两侧低点较低）
        mid = recent_5[2]
        left = recent_5[1]
        right = recent_5[3]

        mid_high = mid.get("high") or 0
        mid_low = mid.get("low") or 0
        left_high = left.get("high") or 0
        left_low = left.get("low") or 0
        right_high = right.get("high") or 0
        right_low = right.get("low") or 0

        # 底分型：中间K线低点最低，两侧低点较高
        is_bottom = mid_low < min(left_low, right_low) and mid_high < max(left_high, right_high)
        # 顶分型：中间K线高点最高，两侧高点较低
        is_top = mid_high > max(left_high, right_high) and mid_low > min(left_low, right_low)

        # 买卖点判断
        if macd_dif > macd_dea and macd_hist < 0:
            signal_type = "一买"
            score = 80
        elif macd_dif > macd_dea and macd_hist >= 0:
            signal_type = "二买"
            score = 85
        elif is_bottom and macd_dif > macd_dea:
            signal_type = "一买"
            score = 85
        elif is_top and macd_dif < macd_dea:
            signal_type = "一卖"
            score = 75
        else:
            return None

        return {
            "signals": [
                {"name": "买卖点", "value": signal_type, "description": "缠论买卖点信号"},
                {"name": "MACD", "value": f"DIF{round(macd_dif, 3)} DEA{round(macd_dea, 3)}", "description": f"HIST{round(macd_hist, 3)}"},
                {"name": "分型", "value": "底分型" if is_bottom else ("顶分型" if is_top else "无"), "description": "K线结构"},
            ],
            "match_reason": f"缠论{signal_type}信号，MACD状态确认",
            "score": round(score, 1),
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # 策略调度器
    # ─────────────────────────────────────────────────────────────────────────────

    STRATEGY_CALC_MAP = {
        "bottom_volume": "calc_bottom_volume",
        "box_oscillation": "calc_box_oscillation",
        "bull_trend": "calc_bull_trend",
        "chan_theory": "calc_chan_theory",
        "ma_golden_cross": "calc_ma_golden_cross",
        "one_yang_three_yin": "calc_one_yang_three_yin",
        "shrink_pullback": "calc_shrink_pullback",
        "volume_breakout": "calc_volume_breakout",
        "wave_theory": "calc_wave_theory",
    }

    def execute_strategy(
        self, strategy_id: str, trade_date: str, limit: int = 20
    ) -> tuple[list[dict], int, dict]:
        """
        执行策略计算，返回 (items, total, stats)
        """
        if strategy_id not in self.STRATEGY_CALC_MAP:
            raise ValueError(f"Unknown strategy: {strategy_id}")

        calc_method = getattr(self, self.STRATEGY_CALC_MAP[strategy_id])

        # 获取全部股票最新数据
        stocks = self.get_all_stocks_latest(trade_date)

        results = []
        for stock in stocks:
            if not stock.get("close"):
                continue

            # 获取历史数据用于策略计算
            hist_days = 120 if strategy_id in ("box_oscillation", "wave_theory") else 30
            daily_history = self.get_daily_history(stock["symbol"], trade_date, days=hist_days)

            if not daily_history:
                continue

            result = calc_method(stock, daily_history)
            if result:
                item = {
                    "symbol": stock["symbol"],
                    "name": stock["name"],
                    "exchange": stock["exchange"],
                    "close": _safe_float(stock.get("close")),
                    "change_pct": _safe_float(stock.get("change_pct")),
                    "turnover_rate": _safe_float(stock.get("turnover_rate")),
                    "ma5": _safe_float(stock.get("ma5")),
                    "ma10": _safe_float(stock.get("ma10")),
                    "ma20": _safe_float(stock.get("ma20")),
                    "volume_ratio": _safe_float(stock.get("volume_ratio")),
                    "trend_score": _safe_float(stock.get("trend_score")),
                    **result,
                }
                results.append(item)

        # 按 score 降序
        results.sort(key=lambda x: x["score"], reverse=True)
        total = len(results)

        # 统计
        top_results = results[:limit]
        avg_trend = sum(r["trend_score"] or 0 for r in results[:100] if r.get("trend_score")) / min(len(results), 100) if results else None
        avg_change = sum(r["change_pct"] or 0 for r in results[:100] if r.get("change_pct") is not None) / min(len(results), 100) if results else None
        avg_turnover = sum(r["turnover_rate"] or 0 for r in results[:100] if r.get("turnover_rate") is not None) / min(len(results), 100) if results else None

        stats = {
            "total_count": total,
            "avg_trend_score": round(avg_trend, 1) if avg_trend else None,
            "avg_change_pct": round(avg_change, 2) if avg_change else None,
            "avg_turnover_rate": round(avg_turnover, 2) if avg_turnover else None,
        }

        return top_results[:limit], total, stats

    def analyze_stock(self, symbol: str, trade_date: str) -> list[dict]:
        """
        问股分析：给定一只股票，用9种策略分别分析它。
        返回每种策略的触发结果、信号和匹配原因。
        """
        # 获取股票最新基础数据
        sql = text("""
            SELECT
                m.symbol, m.name, m.exchange,
                d.close, d.change_pct, d.turnover_rate_f as turnover_rate,
                d.volume, d.amplitude, d.volume_ratio,
                f.ma5, f.ma10, f.ma20, f.ma60, f.ma120,
                f.volume_ma5, f.volume_ma10,
                f.macd_dif, f.macd_dea, f.macd_hist,
                f.high_20, f.high_60, f.low_20, f.low_60,
                f.pct_5d, f.pct_10d, f.pct_20d, f.pct_60d,
                f.rsi_6, f.rsi_14, f.trend_score,
                f.is_new_high_60d, f.is_break_ma20
            FROM dwd_security_master m
            LEFT JOIN dwd_stock_daily d ON d.symbol = m.symbol
                AND d.trade_date = :trade_date
            LEFT JOIN dwd_stock_factor_daily f ON f.symbol = m.symbol
                AND f.trade_date = :trade_date
            WHERE m.symbol = :symbol AND m.status = 'LISTED'
        """)
        result = self.db.execute(sql, {"symbol": symbol, "trade_date": trade_date})
        row = result.mappings().fetchone()
        if not row:
            raise ValueError(f"Stock {symbol} not found or not listed")

        # Decimal → float 转换
        float_fields = (
            "close", "change_pct", "turnover_rate", "volume", "amplitude", "volume_ratio",
            "ma5", "ma10", "ma20", "ma60", "ma120",
            "volume_ma5", "volume_ma10",
            "macd_dif", "macd_dea", "macd_hist",
            "high_20", "high_60", "low_20", "low_60",
            "pct_5d", "pct_10d", "pct_20d", "pct_60d",
            "rsi_6", "rsi_14", "trend_score",
        )
        stock = {k: (_safe_float(v) if k in float_fields and v is not None else v) for k, v in row.items()}
        if not stock.get("close"):
            raise ValueError(f"No trading data for {symbol} on {trade_date}")

        # 获取历史数据
        daily_history = self.get_daily_history(symbol, trade_date, days=120)

        results = []
        for strategy_id, calc_method_name in self.STRATEGY_CALC_MAP.items():
            strategy_meta = STRATEGY_METADATA[strategy_id]
            calc_method = getattr(self, calc_method_name)

            # 根据策略类型决定取多少日历史
            hist_days = 120 if strategy_id in ("box_oscillation", "wave_theory") else 30
            hist = daily_history[-hist_days:] if len(daily_history) >= hist_days else daily_history

            calc_result = calc_method(stock, hist)

            if calc_result:
                results.append({
                    "strategy_id": strategy_id,
                    "strategy_name": strategy_meta["name"],
                    "triggered": True,
                    "score": calc_result["score"],
                    "signals": calc_result["signals"],
                    "match_reason": calc_result["match_reason"],
                    "priority": strategy_meta["priority"],
                })
            else:
                results.append({
                    "strategy_id": strategy_id,
                    "strategy_name": strategy_meta["name"],
                    "triggered": False,
                    "score": 0,
                    "signals": [],
                    "match_reason": "当前不符合该策略条件",
                    "priority": strategy_meta["priority"],
                })

        # 按优先级排序
        results.sort(key=lambda x: x["priority"])
        return results
