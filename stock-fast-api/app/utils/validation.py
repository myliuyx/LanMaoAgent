"""参数校验工具"""
from app.core.exceptions import BizException


def validate_sort_field(
    value: str,
    allowed_fields: set[str],
    field_name: str = "sort_by",
) -> str:
    """
    校验排序字段是否在白名单内，不在则抛 BizException。

    用法：
        sort_by = validate_sort_field(sort_by, {"change_pct", "turnover_rate", "market_value"})

    参数：
        value:          前端传入的排序字段
        allowed_fields: 允许的字段集合（snake_case）
        field_name:     报错时用的字段名
    """
    if value not in allowed_fields:
        raise BizException(
            code=4004,
            message=f"非法排序字段: {value}，允许: {', '.join(sorted(allowed_fields))}",
        )
    return value


def validate_sort_order(value: str) -> str:
    """
    校验排序方向，仅允许 "asc" 或 "desc"，非法值抛 BizException。

    用法：
        sort_order = validate_sort_order(sort_order)
    """
    if value not in ("asc", "desc"):
        raise BizException(
            code=4004,
            message=f"非法排序方向: {value}，允许: asc, desc",
        )
    return value


def validate_symbol(symbol: str | None) -> str | None:
    """
    校验 symbol 格式。A股 symbol 格式应为 XXXXXX.XX（如 600519.SH）。

    用法：
        symbol = validate_symbol(symbol)

    注意：
        目前仅做格式检查，不查库。
        返回 None 表示跳过校验（前端传空时）。
    """
    if symbol is None:
        return None

    # 格式：6位数字 . 2位大写字母
    parts = symbol.split(".")
    if len(parts) != 2 or len(parts[0]) != 6 or not parts[0].isdigit() or len(parts[1]) != 2:
        raise BizException(code=4003, message=f"非法 symbol 格式: {symbol}，期望如 600519.SH")
    return symbol
