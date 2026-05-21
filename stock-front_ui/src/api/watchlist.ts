import request from './request'
import type {
  WatchlistResponse,
  WatchlistAddResponse,
  WatchlistCheckResponse,
} from '@/types/watchlist'

/** 股票代码格式校验 */
const SYMBOL_RE = /^[A-Z0-9.]+$/
function validateSymbol(symbol: string): string {
  if (!SYMBOL_RE.test(symbol)) {
    throw new Error(`非法股票代码: ${symbol}`)
  }
  return symbol
}

export const watchlistApi = {
  /**
   * 获取自选股列表
   * GET /watchlist?page=1&page_size=50
   */
  getList: (params?: { page?: number; page_size?: number }) =>
    request.get<WatchlistResponse>('/watchlist', { params }),

  /**
   * 添加股票到自选
   * POST /watchlist
   */
  add: (symbol: string) =>
    request.post<WatchlistAddResponse>('/watchlist', { symbol }),

  /**
   * 从自选删除股票
   * DELETE /watchlist/{symbol}
   */
  remove: (symbol: string) =>
    request.delete<void>(`/watchlist/${validateSymbol(symbol)}`),

  /**
   * 检查股票是否在自选
   * GET /watchlist/check/{symbol}
   */
  check: (symbol: string) =>
    request.get<WatchlistCheckResponse>(`/watchlist/check/${validateSymbol(symbol)}`),
}