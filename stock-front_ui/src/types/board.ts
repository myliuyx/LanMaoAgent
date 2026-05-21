// 板块类型
export type BoardType = 'INDUSTRY' | 'CONCEPT' | 'INDEX' | 'AREA'

// 板块项
export interface BoardItem {
  board_code: string
  board_name: string
  board_type: BoardType
  member_count: number
  is_active: boolean
}

// 板块详情
export interface BoardDetail {
  board_code: string
  board_name: string
  board_type: BoardType
  parent_board_code: string | null
  is_active: boolean
}

// 成分股项
export interface BoardMember {
  symbol: string
  name: string
  exchange: string
  close: number | null
  change_pct: number | null
  turnover_rate: number | null
  market_value: number | null
  trend_score: number | null
  industry_l1: string | null
  trade_date?: string  // 最近交易日（成分股行情日期）
}
