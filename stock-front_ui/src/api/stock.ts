import request from './request'
import type {
  StockProfile,
  StockDaily,
  StockDailyQuery,
  StockFactor,
  FinancialIndicator,
  StockBoard,
  DataCoverage,
} from '@/types/stock'
import type { CoverageRawResponse } from '@/types/dashboard'

/** 股票代码格式校验（如 600519.SH / 000001.SZ） */
const SYMBOL_RE = /^[A-Z0-9.]+$/
function validateSymbol(symbol: string): string {
  if (!SYMBOL_RE.test(symbol)) {
    throw new Error(`非法股票代码: ${symbol}`)
  }
  return symbol
}

// /coverage/{symbol} 返回的原始数据结构（见 @/types/dashboard.ts CoverageRawResponse）

export const stockApi = {
  search: (keyword: string, limit = 5, signal?: AbortSignal) =>
    request.get<{ symbol: string; name: string; exchange: string }[]>(
      '/stocks/search',
      { params: { keyword, limit }, signal }
    ),

  getProfile: (symbol: string) =>
    request.get<StockProfile>(`/stocks/${validateSymbol(symbol)}/profile`),

  getDaily: (symbol: string, params?: StockDailyQuery) =>
    request.get<StockDaily[]>(`/stocks/${validateSymbol(symbol)}/daily`, { params }),

  getFactors: (symbol: string, params?: { trade_date?: string; limit?: number }) =>
    request.get<StockFactor[]>(`/stocks/${validateSymbol(symbol)}/factors`, { params }),

  getFinance: (symbol: string, limit = 8) =>
    request.get<FinancialIndicator[]>(`/stocks/${validateSymbol(symbol)}/finance`, { params: { limit } }),

  getBoards: (symbol: string) =>
    request.get<StockBoard[]>(`/stocks/${validateSymbol(symbol)}/boards`),

  /**
   * 数据覆盖信息。
   * 路由：GET /coverage/{symbol}
   * 后端返回 {symbol, name, coverages}，此处拆平成 DataCoverage[]
   * request.get 返回 ApiResponse<T>，所以 res.data 是 CoverageRawResponse
   */
  getCoverage: async (symbol: string): Promise<DataCoverage[]> => {
    const validated = validateSymbol(symbol)
    const res = await request.get<CoverageRawResponse>(`/coverage/${validated}`)
    const data = res.data
    if (!data || !data.coverages?.length) return []
    return data.coverages.map((c) => ({
      symbol: data.symbol,
      name: data.name,
      data_type: c.data_type as DataCoverage['data_type'],
      start_date: c.start_date,
      end_date: c.end_date,
      is_full_history: c.is_full_history,
      last_sync_at: c.last_sync_at,
    }))
  },
}
