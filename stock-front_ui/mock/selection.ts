export default [
  {
    url: '/api/v1/selection/dates',
    method: 'get',
    response: () => ({
      code: 0,
      message: 'ok',
      data: ['2026-04-18', '2026-04-17', '2026-04-16', '2026-04-15', '2026-04-14'],
    }),
  },
  {
    url: '/api/v1/selection/industries',
    method: 'get',
    response: () => ({
      code: 0,
      message: 'ok',
      data: ['白酒', '锂电池', '半导体', '光伏设备', '医疗器械', '化学制药', '白酒', '银行', '证券', '房地产'],
    }),
  },
  {
    url: '/api/v1/selection/results',
    method: 'get',
    response: ({ query }: any) => {
      const items = [
        { symbol: '600519.SH', name: '贵州茅台', exchange: 'SH', industry_l1: '白酒', trend_score: 92.5, pct_change: 3.25, pct_change_5d: 8.12, pct_change_20d: 15.33, turnover_rate: 1.28, float_share: 124154.22, is_st: false, trade_date: '2026-04-18', is_new: false },
        { symbol: '300750.SZ', name: '宁德时代', exchange: 'SZ', industry_l1: '锂电池', trend_score: 88.3, pct_change: 5.67, pct_change_5d: 12.44, pct_change_20d: 22.18, turnover_rate: 3.45, float_share: 216637.88, is_st: false, trade_date: '2026-04-18', is_new: false },
        { symbol: '000858.SZ', name: '五粮液', exchange: 'SZ', industry_l1: '白酒', trend_score: 85.1, pct_change: 2.18, pct_change_5d: 6.33, pct_change_20d: 11.52, turnover_rate: 1.56, float_share: 38655.46, is_st: false, trade_date: '2026-04-18', is_new: false },
        { symbol: '688041.SH', name: '寒武纪', exchange: 'SH', industry_l1: '半导体', trend_score: 91.8, pct_change: 12.45, pct_change_5d: 25.67, pct_change_20d: 45.23, turnover_rate: 8.92, float_share: 28345.67, is_st: false, trade_date: '2026-04-18', is_new: false },
        { symbol: '300760.SZ', name: '迈瑞医疗', exchange: 'SZ', industry_l1: '医疗器械', trend_score: 82.4, pct_change: 1.89, pct_change_5d: 4.22, pct_change_20d: 9.87, turnover_rate: 1.12, float_share: 45678.90, is_st: false, trade_date: '2026-04-18', is_new: false },
        { symbol: '002475.SZ', name: '立讯精密', exchange: 'SZ', industry_l1: '电子制造', trend_score: 79.6, pct_change: 0.56, pct_change_5d: 2.33, pct_change_20d: 7.12, turnover_rate: 0.98, float_share: 78934.12, is_st: false, trade_date: '2026-04-18', is_new: false },
      ]
      const page = Number(query.page ?? 1)
      const pageSize = Number(query.page_size ?? 10)
      const filtered = items.filter(i => !query.industry_l1 || query.industry_l1 === '' || i.industry_l1 === query.industry_l1)
      return {
        code: 0,
        message: 'ok',
        data: {
          list: filtered.slice((page - 1) * pageSize, page * pageSize),
          total: filtered.length,
          page,
          page_size: pageSize,
        },
      }
    },
  },
]
