# Utils 层 - 工具函数

> 跨层复用的通用工具，**不含任何业务逻辑**。

## 文件清单

| 文件 | 导出 | 说明 |
|------|------|------|
| `pagination.py` | `paginate()`, `clamp_page_size()` | 分页构建 |
| `validation.py` | `validate_sort_field()`, `validate_sort_order()`, `validate_symbol()`, `validate_page()` | 参数校验 |

## pagination.py

### `paginate(data, page, page_size) -> dict`

对 list 进行分页切片，返回统一分页结构。所有 Repository 的分页查询统一使用此函数。

```python
from app.utils.pagination import paginate

# 替代手动写：
# start = (page - 1) * page_size
# return {"list": data[start:end], "page": page, "page_size": page_size, "total": len(data)}

return paginate(filtered, page, page_size)
```

### `clamp_page_size(page_size, default=20, max_val=100) -> int`

将 page_size 钳制在 [1, max_val] 范围内，防止恶意传入负数或极大值。

```python
from app.utils.pagination import clamp_page_size

page_size = clamp_page_size(req.page_size)  # 负数 → 20，过大 → 100
```

## validation.py

### `validate_sort_field(value, allowed_fields, field_name="sort_by") -> str`

校验排序字段是否在白名单内，不在则抛 `BizException(code=4004)`。

```python
from app.utils.validation import validate_sort_field

sort_by = validate_sort_field(
    sort_by,
    {"change_pct", "turnover_rate", "market_value"},
)
```

### `validate_sort_order(value) -> str`

校验排序方向，仅允许 `asc` / `desc`，非法默认返回 `"desc"`。

### `validate_symbol(symbol) -> str | None`

校验 A 股 symbol 格式（XXXXXX.XX），非法抛 `BizException(code=4003)`。None 跳过校验。

```python
symbol = validate_symbol(symbol)  # "600519.SH" → "600519.SH"
```

### `validate_page(page) -> int`

page 必须 >= 1，非法返回 1。

---

## 迁移记录

| 日期 | 动作 |
|------|------|
| 2026-04-18 | 创建 pagination.py / validation.py |
| 2026-04-18 | board_repository.py / coverage_repository.py 迁入 paginate() |
