"""分页工具"""
from typing import List, TypeVar

T = TypeVar("T")


def paginate(data: List[T], page: int, page_size: int) -> dict:
    """
    对 list 进行分页切片，返回统一分页结构。

    用法：
        return paginate(filtered, page, page_size)

    返回：
        {
            "list": List[T],   # 当前页数据
            "page": int,       # 当前页码
            "page_size": int,  # 每页大小
            "total": int,      # 总记录数
        }
    """
    page = max(1, page)
    page_size = clamp_page_size(page_size)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "list": data[start:end],
        "page": page,
        "page_size": page_size,
        "total": len(data),
    }


def clamp_page_size(page_size: int, default: int = 20, max_val: int = 100) -> int:
    """
    将 page_size 钳制在 [1, max_val] 范围内，防止恶意传入负数或极大值。

    用法：
        page_size = clamp_page_size(req.page_size)

    参数：
        default: page_size <= 0 时使用的默认值
        max_val: 上限
    """
    if page_size <= 0:
        return default
    return min(page_size, max_val)
