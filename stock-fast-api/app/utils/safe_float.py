"""通用数据转换工具"""
import math
import re
from typing import Optional


def _safe_float(val):
    """Handle NaN and Inf values that break JSON serialization."""
    if val is None:
        return None
    v = float(val)
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def _clean_industry(raw: Optional[str]) -> Optional[str]:
    """清理 industry_l1 的分类前缀（如 'C15酒、饮料...' → '酒、饮料...'）"""
    if not raw:
        return None
    return re.sub(r"^[A-Z]\d+", "", raw).lstrip("_ ")
