import type { PageResponse } from './common'

export interface WatchlistItem {
  // 基础字段
  symbol: string        // e.g. "600519.SH"
  name: string
  exchange: string      // "SH" | "SZ"
  added_at: string
  close: number | null
  change_pct: number | null
  turnover_rate: number | null
  trend_score: number | null

  // 52周价格区间
  price_52w_high: number | null      // 52周最高价
  price_52w_low: number | null      // 52周最低价
  price_percentile: number | null    // 价格分位 0-100
  dist_to_52w_high_pct: number | null  // 距52周高点跌幅%
  dist_to_52w_low_pct: number | null    // 距52周低点涨幅%

  // MA5均线
  ma5: number | null           // 5日均线
  price_vs_ma5_pct: number | null  // 股价相对MA5位置%

  // 振幅 & 估值
  amplitude: number | null     // 振幅%
  pe_ttm: number | null        // 市盈率TTM
  pb: number | null            // 市净率
}

export type WatchlistResponse = PageResponse<WatchlistItem>

export interface WatchlistAddResponse {
  symbol: string
  added_at: string
}

export interface WatchlistCheckResponse {
  symbol: string
  in_watchlist: boolean
}