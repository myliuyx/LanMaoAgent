// 生成 K 线数据
function generateDaily(symbol: string, count = 120) {
  const list = []
  const basePrice = symbol === '600519.SH' ? 1680 : symbol === '300750.SZ' ? 520 : 100
  let price = basePrice
  const today = new Date('2026-04-18')

  for (let i = count; i >= 0; i--) {
    const date = new Date(today)
    date.setDate(date.getDate() - i)
    const dateStr = date.toISOString().substring(0, 10)
    const change = (Math.random() - 0.48) * price * 0.03
    const open = price
    const close = price + change
    const high = Math.max(open, close) * (1 + Math.random() * 0.015)
    const low = Math.min(open, close) * (1 - Math.random() * 0.015)
    const volume = Math.floor(Math.random() * 5000000 + 1000000)
    list.push({
      trade_date: dateStr,
      open: +open.toFixed(2),
      high: +high.toFixed(2),
      low: +low.toFixed(2),
      close: +close.toFixed(2),
      volume,
      amount: +(volume * close).toFixed(2),
      change: +change.toFixed(2),
      change_pct: +(change / price * 100).toFixed(2),
      turnover_rate: +(Math.random() * 2).toFixed(3),
    })
    price = close
  }
  return list
}

const PROFILES: Record<string, any> = {
  '600519.SH': { symbol: '600519.SH', name: '贵州茅台', exchange: 'SH', ticker: '600519', security_type: 'Common Stock', list_board: '主板', list_date: '2001-08-27', delist_date: null, status: 'LISTED', is_st: false, industry_l1: '白酒', industry_l2: '高端白酒', area: '贵州' },
  '300750.SZ': { symbol: '300750.SZ', name: '宁德时代', exchange: 'SZ', ticker: '300750', security_type: 'Common Stock', list_board: '创业板', list_date: '2018-06-11', delist_date: null, status: 'LISTED', is_st: false, industry_l1: '锂电池', industry_l2: '动力电池', area: '福建' },
  '000858.SZ': { symbol: '000858.SZ', name: '五粮液', exchange: 'SZ', ticker: '000858', security_type: 'Common Stock', list_board: '主板', list_date: '1998-04-27', delist_date: null, status: 'LISTED', is_st: false, industry_l1: '白酒', industry_l2: '高端白酒', area: '四川' },
}

export default [
  {
    url: '/api/v1/stocks/search',
    method: 'get',
    response: ({ query }: any) => ({
      code: 0,
      message: 'ok',
      data: [
        { symbol: '600519.SH', name: '贵州茅台', exchange: 'SH' },
        { symbol: '300750.SZ', name: '宁德时代', exchange: 'SZ' },
        { symbol: '000858.SZ', name: '五粮液', exchange: 'SZ' },
      ].filter(s => s.name.includes(query.keyword || '')),
    }),
  },
  {
    url: '/api/v1/stocks/:symbol/profile',
    method: 'get',
    response: ({ params }: any) => ({
      code: 0,
      message: 'ok',
      data: PROFILES[params.symbol] || { symbol: params.symbol, name: '未知股票', exchange: 'SH', industry: '未知', market: '主板', list_date: '2020-01-01', is_st: false, total_shares: 0, float_shares: 0 },
    }),
  },
  {
    url: '/api/v1/stocks/:symbol/daily',
    method: 'get',
    response: ({ params }: any) => ({
      code: 0,
      message: 'ok',
      data: generateDaily(params.symbol),
    }),
  },
  {
    url: '/api/v1/stocks/:symbol/factors',
    method: 'get',
    response: ({ params }: any) => {
      const list = []
      const today = new Date('2026-04-18')
      for (let i = 30; i >= 0; i--) {
        const d = new Date(today)
        d.setDate(d.getDate() - i)
        list.push({
          trade_date: d.toISOString().substring(0, 10),
          pe_ttm: +(20 + Math.random() * 30).toFixed(2),
          pb: +(2 + Math.random() * 5).toFixed(2),
          ps_ttm: +(5 + Math.random() * 15).toFixed(2),
          dv_ratio: +(1 + Math.random() * 4).toFixed(2),
          dv_ttm: +(0.5 + Math.random() * 3).toFixed(2),
        })
      }
      return { code: 0, message: 'ok', data: list }
    },
  },
  {
    url: '/api/v1/stocks/:symbol/finance',
    method: 'get',
    response: () => ({
      code: 0,
      message: 'ok',
      data: [
        { report_date: '2025-12-31', revenue: 158512, net_profit: 88215, roe: 30.2, gross_margin: 91.97, asset_liab_ratio: 18.93 },
        { report_date: '2025-09-30', revenue: 120796, net_profit: 66823, roe: 23.1, gross_margin: 91.86, asset_liab_ratio: 19.45 },
        { report_date: '2025-06-30', revenue: 78024, net_profit: 43214, roe: 15.3, gross_margin: 91.94, asset_liab_ratio: 20.12 },
        { report_date: '2025-03-31', revenue: 38823, net_profit: 24154, roe: 8.2, gross_margin: 91.88, asset_liab_ratio: 21.33 },
        { report_date: '2024-12-31', revenue: 153563, net_profit: 86287, roe: 31.0, gross_margin: 91.93, asset_liab_ratio: 17.12 },
      ],
    }),
  },
  {
    url: '/api/v1/stocks/:symbol/boards',
    method: 'get',
    response: ({ params }: any) => ({
      code: 0,
      message: 'ok',
      data: [
        { board_code: 'BK0001', board_name: '白酒行业', board_type: 'INDUSTRY', relation: '所属', weight: 15.2 },
        { board_code: 'BK0002', board_name: '上证50成分', board_type: 'INDEX_CONST', relation: '所属', weight: 3.8 },
        { board_code: 'BK0003', board_name: '超级品牌', board_type: 'CONCEPT', relation: '概念', weight: 8.5 },
      ],
    }),
  },
  {
    url: '/api/v1/stocks/:symbol/coverage',
    method: 'get',
    response: () => ({
      code: 0,
      message: 'ok',
      data: [
        { data_type: 'DAILY', start_date: '2001-08-27', end_date: '2026-04-18', is_full_history: true, last_sync_at: '2026-04-18T08:30:00' },
        { data_type: 'FINANCE', start_date: '2001-12-31', end_date: '2025-12-31', is_full_history: true, last_sync_at: '2026-04-18T09:00:00' },
        { data_type: 'ADJUST_FACTOR', start_date: '2001-08-27', end_date: '2026-04-18', is_full_history: true, last_sync_at: '2026-04-18T07:00:00' },
      ],
    }),
  },
]
