// 自选股分析结果
export interface WatchlistAnalysisResult {
  summary: {
    total: number
    up_count: number
    down_count: number
    near_high_count: number
    near_low_count: number
    bullish_count: number
    volume_alert_count: number
    up_rate: number
  }
  stocks: WatchlistStockAnalysis[]
}

export interface WatchlistStockAnalysis {
  symbol: string
  name: string
  close: number | null
  change_pct: number | null
  turnover_rate: number | null
  high_52w: number | null
  low_52w: number | null
  near_high: boolean
  near_low: boolean
  ma5: number | null
  ma10: number | null
  ma20: number | null
  ma60: number | null
  bullish: boolean
  bearish: boolean
  volume_spike: boolean
  momentum: number | null
  signals: string[]
}

// 仪表盘概要
export interface DashboardSummary {
  latest_trade_date: string
  is_trade_day: boolean
  stock_count: number
  daily_record_count: number
  finance_record_count: number
  factor_record_count: number
  today_job_success_count: number
  today_job_failed_count: number
  selection_count: number
}

// 数据覆盖概要
export interface CoverageSummary {
  total_symbols: number
  daily_fully_covered_symbols: number
  financial_fully_covered_symbols: number
  adjust_factor_fully_covered_symbols: number
}

// /coverage/{symbol} 返回的原始数据结构
export interface CoverageRawResponse {
  symbol: string
  name: string
  coverages: {
    data_type: string
    start_date: string
    end_date: string
    is_full_history: boolean
    last_sync_at: string
  }[]
}