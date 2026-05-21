import request from './request'
import type { PageResponse } from '@/types/common'
import type { DataCoverage } from '@/types/stock'

/** 股票代码格式校验 */
const SYMBOL_RE = /^[A-Z0-9.]+$/
function validateSymbol(symbol: string): string {
  if (!SYMBOL_RE.test(symbol)) {
    throw new Error(`非法股票代码: ${symbol}`)
  }
  return symbol
}

export const coverageApi = {
  getList: (params?: {
    symbol?: string
    data_type?: string
    is_full_history?: boolean
    page?: number
    page_size?: number
  }) => request.get<PageResponse<DataCoverage>>('/coverage', { params }),

  getDetail: (symbol: string) =>
    request.get<{ symbol: string; name: string; coverages: DataCoverage[] }>(
      `/coverage/${validateSymbol(symbol)}`
    ),
}
