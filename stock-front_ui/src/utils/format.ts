// 日期格式化：兼容 ISO 字符串 / YYYY-MM-DD / YYYY-MM-DDTHH:mm:ss 等格式
// 输出统一为 YYYY-MM-DD 或 YYYY-MM-DD HH:mm:ss
const DATE_ONLY_RE = /^\d{4}-\d{2}-\d{2}$/
export const formatDate = (dateStr: string | null | undefined, showTime = false): string => {
  if (!dateStr) return '-'
  // 已经是 YYYY-MM-DD，直接返回
  if (DATE_ONLY_RE.test(dateStr)) return dateStr
  // 截断 ISO 字符串的 T 部分，保留日期时间
  const idx = dateStr.indexOf('T')
  const d = idx >= 0 ? dateStr.substring(0, idx) : dateStr
  if (!showTime) return d
  // 追加时间部分（去掉 UTC Z 后缀）
  const timePart = idx >= 0 ? dateStr.substring(idx + 1).replace(/\.\d+Z?$/, '') : ''
  return timePart ? `${d} ${timePart}` : d
}

// 大数量格式化：超过1万显示为 万，超过1亿显示为 亿
// 用于 日线数据、财务数据、技术因子 等字段
export const fmtCount = (num: number | null | undefined): string => {
  if (num === null || num === undefined) return '-'
  if (num >= 1e8) return (num / 1e8).toFixed(1) + '亿'
  if (num >= 1e4) return (num / 1e4).toFixed(1) + '万'
  return num.toLocaleString('zh-CN')
}

// 千分位格式化（用于不需要 万/亿 的场景）
export const formatNumber = (num: number | null | undefined, decimals = 2): string => {
  if (num === null || num === undefined) return '-'
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

// 金额格式化：万/亿
export const formatMoney = (amount: number | null | undefined): string => {
  if (amount === null || amount === undefined) return '-'
  if (amount >= 1e8) return (amount / 1e8).toFixed(2) + '亿'
  if (amount >= 1e4) return (amount / 1e4).toFixed(2) + '万'
  return amount.toFixed(2)
}

// 百分比格式化
export const formatPercent = (pct: number | null | undefined, decimals = 2): string => {
  if (pct === null || pct === undefined) return '-'
  return pct.toFixed(decimals) + '%'
}

// 涨跌额颜色
export const getChangeColor = (change: number | null | undefined): string => {
  if (change === null || change === undefined) return ''
  if (change > 0) return '#F56C6C' // 红色涨
  if (change < 0) return '#67C23A' // 绿色跌
  return ''
}

// 涨跌符号
export const getChangeSign = (change: number | null | undefined): string => {
  if (change === null || change === undefined) return ''
  if (change > 0) return '+'
  return ''
}

// 耗时格式化：毫秒 -> 分:秒
export const formatDuration = (ms: number | null | undefined): string => {
  if (ms === null || ms === undefined) return '-'
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  if (minutes > 0) return `${minutes}分${remainingSeconds}秒`
  return `${seconds}秒`
}

// ─── 自选股表格辅助函数 ─────────────────────────────────────────

export const getExchangeLabel = (exchange: string): string => {
  return exchange === 'SH' ? '上交所' : exchange === 'SZ' ? '深交所' : exchange === 'BJ' ? '北交所' : exchange
}

export const getScoreType = (score: number | null): 'success' | 'warning' | 'danger' | 'info' => {
  if (score === null) return 'info'
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

export const getPercentileType = (p: number | null): 'success' | 'warning' | 'danger' | 'info' => {
  if (p === null) return 'info'
  if (p >= 80) return 'danger'
  if (p <= 20) return 'success'
  if (p >= 60) return 'warning'
  return 'info'
}

export const getDistColor = (d: number | null, isHigh: boolean): string => {
  if (d === null) return 'var(--color-text-muted)'
  if (isHigh) return d >= 0 ? '#67C23A' : '#F56C6C'
  return d >= 0 ? '#F56C6C' : '#67C23A'
}

export const getPEType = (v: number | null): 'success' | 'warning' | 'danger' | 'info' => {
  if (v === null) return 'info'
  if (v < 0) return 'danger'
  if (v > 100) return 'danger'
  if (v > 50) return 'warning'
  return 'info'
}

export const getPBType = (v: number | null): 'success' | 'warning' | 'danger' | 'info' => {
  if (v === null) return 'info'
  if (v < 0) return 'danger'
  if (v > 20) return 'danger'
  if (v > 5) return 'warning'
  return 'info'
}

export const getVsMA5Color = (p: number | null): string => {
  if (p === null) return 'var(--color-text-muted)'
  return p >= 0 ? '#F56C6C' : '#67C23A'
}

export const formatPercentile = (p: number | null): string => {
  if (p === null) return '-'
  return `${p.toFixed(1)}%`
}

export const formatDist = (d: number | null): string => {
  if (d === null) return '-'
  const sign = d >= 0 ? '+' : ''
  return `${sign}${d.toFixed(1)}%`
}

export const formatVsMA5 = (p: number | null): string => {
  if (p === null) return '-'
  const sign = p >= 0 ? '+' : ''
  return `${sign}${p.toFixed(2)}%`
}

export const formatAmplitude = (a: number | null): string => {
  if (a === null) return '-'
  return `${a.toFixed(2)}%`
}

export const formatMA5 = (m: number | null): string => {
  if (m === null) return '-'
  return formatNumber(m, 2)
}

export const formatPE = (v: number | null): string => {
  if (v === null) return '-'
  return formatNumber(v, 2)
}

