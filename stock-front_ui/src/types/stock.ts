// 股票资料
export interface StockProfile {
  symbol: string
  name: string
  exchange: string
  ticker: string
  security_type: string | null
  list_board: string | null
  list_date: string | null
  delist_date: string | null
  status: 'LISTED' | 'DELISTED' | 'SUSPENDED' | null
  is_st: boolean
  industry_l1: string | null
  industry_l2: string | null
  area: string | null
}

// 日线行情
export interface StockDaily {
  trade_date: string
  open: number
  high: number
  low: number
  close: number
  pre_close: number
  change_amount: number
  change_pct: number
  volume: number
  amount: number
  turnover_rate: number
  amplitude: number
  market_value: number
  circ_market_value: number
}

// 日线查询参数
export interface StockDailyQuery {
  start_date?: string
  end_date?: string
  limit?: number
  adjust?: 'none' | 'forward' | 'backward'
}

// 技术因子
export interface StockFactor {
  trade_date: string
  ma5: number | null
  ma10: number | null
  ma20: number | null
  ma60: number | null
  rsi_6: number | null
  rsi_14: number | null
  atr_14: number | null
  macd_dif: number | null
  macd_dea: number | null
  macd_hist: number | null
  is_new_high_60d: boolean
  is_break_ma20: boolean
  trend_score: number | null
}

// 财务指标
export interface FinancialIndicator {
  report_period: string
  report_type: 'Q1' | 'H1' | 'Q3' | 'FY'
  announce_date: string
  eps: number | null
  bps: number | null
  roe: number | null
  gross_margin: number | null
  net_margin: number | null
  revenue: number | null
  net_profit: number | null
  revenue_yoy: number | null
  net_profit_yoy: number | null
  ocf: number | null
}

// 所属板块
export interface StockBoard {
  board_code: string
  board_name: string
  board_type: 'INDUSTRY' | 'CONCEPT' | 'INDEX' | 'AREA'
  update_date: string
}

// 数据覆盖
export interface DataCoverage {
  symbol: string
  name?: string
  data_type: 'DAILY' | 'FINANCE' | 'ADJUST_FACTOR' | 'FACTOR'
  start_date: string | null
  end_date: string | null
  is_full_history: boolean
  last_sync_at: string | null
}
