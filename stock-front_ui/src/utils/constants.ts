// 任务状态枚举映射
export const JOB_STATUS_MAP: Record<string, { label: string; type: string }> = {
  PENDING: { label: '排队中', type: 'info' },
  RUNNING: { label: '运行中', type: 'warning' },
  SUCCESS: { label: '成功', type: 'success' },
  FAILED: { label: '失败', type: 'danger' },
  CANCELLED: { label: '已取消', type: 'info' },
  PARTIAL: { label: '部分成功', type: 'warning' },
}

// 板块类型映射
export const BOARD_TYPE_MAP: Record<string, { label: string }> = {
  INDUSTRY: { label: '行业' },
  CONCEPT: { label: '概念' },
  INDEX: { label: '指数' },
  AREA: { label: '地域' },
}

// 数据类型映射
export const DATA_TYPE_MAP: Record<string, { label: string }> = {
  DAILY: { label: '日线行情' },
  FINANCE: { label: '财务指标' },
  ADJUST_FACTOR: { label: '复权因子' },
  FACTOR: { label: '技术因子' },
}

// 复权类型映射
export const ADJUST_TYPE_MAP: Record<string, { label: string }> = {
  none: { label: '不复权' },
  forward: { label: '前复权' },
  backward: { label: '后复权' },
}

// 报告类型映射
export const REPORT_TYPE_MAP: Record<string, { label: string }> = {
  Q1: { label: '一季报' },
  H1: { label: '半年报' },
  Q3: { label: '三季报' },
  FY: { label: '年报' },
}

// 证券状态映射
export const SECURITY_STATUS_MAP: Record<string, { label: string; type: string }> = {
  LISTED: { label: '上市', type: 'success' },
  DELISTED: { label: '退市', type: 'danger' },
  SUSPENDED: { label: '停牌', type: 'warning' },
}

// 交易所映射
export const EXCHANGE_MAP: Record<string, { label: string }> = {
  SH: { label: '上海' },
  SZ: { label: '深圳' },
  BJ: { label: '北京' },
}

// 分页默认配置
export const DEFAULT_PAGE_SIZE = 50
export const MAX_PAGE_SIZE = 200

// 轮询间隔（毫秒）
export const JOB_POLL_INTERVAL = 10000
