import request from './request'
import type { Strategy, StrategyQueryRequest, StrategyQueryResponse } from '@/types/strategy'

export const strategyApi = {
  /** 获取全部策略列表 */
  listStrategies: () =>
    request.get<Strategy[]>('/strategies'),

  /** 获取单个策略详情 */
  getStrategyInfo: (strategyId: string) =>
    request.get<Strategy>(`/strategies/${strategyId}`),

  /** 执行策略查询（从全市场筛选符合某策略的股票） */
  queryStrategy: (req: StrategyQueryRequest) =>
    request.post<StrategyQueryResponse>('/strategies/query', req),

  /** 问股分析（分析单只股票在9种策略下的表现） */
  analyzeStock: (symbol: string, tradeDate?: string) =>
    request.post<StrategyAnalyzeResponse>('/strategies/analyze', {
      symbol,
      trade_date: tradeDate,
    }),
}

// 问股分析响应类型（内联，避免循环依赖）
export interface StrategyAnalysisResult {
  strategy_id: string
  strategy_name: string
  triggered: boolean
  score: number
  signals: { name: string; value: string | number | boolean; description: string }[]
  match_reason: string
  priority: number
}

export interface StrategyAnalyzeResponse {
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
  trade_date: string
  results: StrategyAnalysisResult[]
}