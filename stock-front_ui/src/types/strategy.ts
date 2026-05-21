// 策略信号
export interface StrategySignal {
  name: string
  value: string | number | boolean
  description: string
}

// 策略元信息
export interface Strategy {
  id: string
  name: string
  name_en: string
  description: string
  priority: number
  market_state: string
  signals: string[]
}

// 策略选股结果项
export interface StrategyStockItem {
  symbol: string
  name: string
  exchange: string
  close: number | null
  change_pct: number | null
  turnover_rate: number | null
  ma5: number | null
  ma10: number | null
  ma20: number | null
  volume_ratio: number | null
  trend_score: number | null
  signals: StrategySignal[]
  match_reason: string
  score: number
}

// 策略查询请求
export interface StrategyQueryRequest {
  strategy_id: string
  trade_date: string
  limit?: number
  page?: number
  page_size?: number
}

// 策略查询统计
export interface StrategyStats {
  total_count: number
  avg_trend_score: number | null
  avg_change_pct: number | null
  avg_turnover_rate: number | null
}

// 策略查询响应
export interface StrategyQueryResponse {
  strategy: Strategy
  items: StrategyStockItem[]
  total: number
  stats: StrategyStats
}