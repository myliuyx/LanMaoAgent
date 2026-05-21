// 选股筛选条件
export interface SelectionFilters {
  keyword?: string
  exchange?: string
  industry_l1?: string   // 一级行业筛选
  is_st?: boolean
  market_value_min?: number
  market_value_max?: number
  turnover_rate_min?: number
  turnover_rate_max?: number
  roe_min?: number
  roe_max?: number
  revenue_yoy_min?: number
  net_profit_yoy_min?: number
  is_new_high_60d?: boolean
  is_break_ma20?: boolean
  trend_score_min?: number
}

// 选股查询请求
export interface SelectionQueryRequest {
  trade_date: string
  filters?: SelectionFilters
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

// 选股Top榜项
export interface SelectionTopItem {
  symbol: string
  name: string
  exchange: string
  industry_l1: string | null
  selection_count: number
  avg_trend_score: number | null
  avg_roe: number | null
  avg_revenue_yoy: number | null
  avg_net_profit_yoy: number | null
  high_60d_count: number
  break_ma20_count: number
  latest_date: string | null
  close: number | null
  change_pct: number | null
  turnover_rate: number | null
  is_new_high_60d: boolean
  is_break_ma20: boolean
}

// 选股结果项
export interface SelectionItem {
  symbol: string
  name: string
  exchange: string
  industry_l1: string | null
  close: number | null
  change_pct: number | null
  turnover_rate: number | null
  market_value: number | null
  roe: number | null
  revenue_yoy: number | null
  net_profit_yoy: number | null
  ma20: number | null
  ma60: number | null
  is_new_high_60d: boolean | null
  trend_score: number | null
  is_st: boolean
  pct_change_5d?: number | null
  pct_change_20d?: number | null
  is_new?: boolean
}
