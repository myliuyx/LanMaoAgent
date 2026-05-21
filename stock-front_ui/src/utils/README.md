# Utils（工具函数）文档

> 本目录包含项目通用的工具函数和常量定义。

---

## 文件索引

| 文件 | 用途 |
|------|------|
| `format.ts` | 格式化工具（日期、金额、百分比、涨跌等） |
| `constants.ts` | 常量定义（枚举映射、分页默认值、轮询间隔等） |

---

## format.ts - 格式化工具

所有函数均为纯函数，无副作用，直接返回字符串。

### 日期格式化

#### `formatDate(dateStr: string): string`
- 日期格式化，直接返回（格式已统一为 YYYY-MM-DD）
- 空值返回 `-`

```typescript
formatDate('2026-04-07') // '2026-04-07'
formatDate('')           // '-'
```

### 数字格式化

#### `formatNumber(num, decimals?)`
- 数字千分位格式化
- 空值返回 `-`

```typescript
formatNumber(1234567.89, 2) // '1,234,567.89'
formatNumber(null)          // '-'
```

#### `formatMoney(amount)`
- 金额格式化，自动转为 万/亿 单位
- 空值返回 `-`

```typescript
formatMoney(1800000000000) // '18000.00亿'
formatMoney(500000)         // '50.00万'
formatMoney(null)           // '-'
```

#### `formatPercent(pct, decimals?)`
- 百分比格式化，自动加 `%` 后缀
- 空值返回 `-`

```typescript
formatPercent(5.23, 2) // '5.23%'
formatPercent(null)    // '-'
```

### 涨跌相关

#### `getChangeColor(change)`
- 根据涨跌返回颜色值
- 涨（>0）→ `#F56C6C`（红色），跌（<0）→ `#67C23A`（绿色），平 → 空字符串

```typescript
getChangeColor(1.23)  // '#F56C6C'
getChangeColor(-0.5) // '#67C23A'
getChangeColor(0)    // ''
```

#### `getChangeSign(change)`
- 返回涨跌符号
- 涨 → `+`，跌 → `''`，平 → `''`

```typescript
getChangeSign(1.23)  // '+'
getChangeSign(-0.5)  // ''
```

### 其他

#### `formatDuration(ms)`
- 耗时格式化：毫秒 → 分:秒
- 空值返回 `-`

```typescript
formatDuration(125000)  // '2分5秒'
formatDuration(30000)   // '30秒'
formatDuration(null)    // '-'
```

#### `formatSymbol(symbol)`
- 股票代码格式化（目前直接返回）
- 后续可扩展：600519.SH → 贵州茅台 等

```typescript
formatSymbol('600519.SH') // '600519.SH'
```

---

## constants.ts - 常量定义

### 任务状态映射

```typescript
JOB_STATUS_MAP: Record<string, { label: string; type: string }>
```

| 状态 | label | type（Element Plus Tag） |
|------|-------|--------------------------|
| PENDING | 排队中 | info |
| RUNNING | 运行中 | warning |
| SUCCESS | 成功 | success |
| FAILED | 失败 | danger |
| CANCELLED | 已取消 | info |

### 板块类型映射

```typescript
BOARD_TYPE_MAP: Record<string, { label: string }>
```

| 类型 | label |
|------|-------|
| INDUSTRY | 行业 |
| CONCEPT | 概念 |
| INDEX | 指数 |
| AREA | 地域 |

### 数据类型映射

```typescript
DATA_TYPE_MAP: Record<string, { label: string }>
```

| 类型 | label |
|------|-------|
| DAILY | 日线行情 |
| FINANCE | 财务指标 |
| ADJUST_FACTOR | 复权因子 |

### 复权类型映射

```typescript
ADJUST_TYPE_MAP: Record<string, { label: string }>
```

| 类型 | label |
|------|-------|
| none | 不复权 |
| forward | 前复权 |
| backward | 后复权 |

### 报告类型映射

```typescript
REPORT_TYPE_MAP: Record<string, { label: string }>
```

| 类型 | label |
|------|-------|
| Q1 | 一季报 |
| H1 | 半年报 |
| Q3 | 三季报 |
| FY | 年报 |

### 证券状态映射

```typescript
SECURITY_STATUS_MAP: Record<string, { label: string; type: string }>
```

| 状态 | label | type |
|------|-------|------|
| LISTED | 上市 | success |
| DELISTED | 退市 | danger |
| SUSPENDED | 停牌 | warning |

### 交易所映射

```typescript
EXCHANGE_MAP: Record<string, { label: string }>
```

| 交易所 | label |
|--------|-------|
| SH | 上海 |
| SZ | 深圳 |
| BJ | 北京 |

### 全局配置常量

```typescript
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
JOB_POLL_INTERVAL = 10000  // 任务轮询间隔（毫秒）
```
