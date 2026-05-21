export default [
  {
    url: '/api/v1/coverage',
    method: 'get',
    response: ({ query }: any) => {
      const all = [
        { symbol: '600519.SH', name: '贵州茅台', exchange: 'SH', data_type: 'DAILY', start_date: '2001-08-27', end_date: '2026-04-18', is_full_history: true, last_sync_at: '2026-04-18T08:30:00' },
        { symbol: '300750.SZ', name: '宁德时代', exchange: 'SZ', data_type: 'DAILY', start_date: '2018-06-11', end_date: '2026-04-18', is_full_history: true, last_sync_at: '2026-04-18T08:30:00' },
        { symbol: '688041.SH', name: '寒武纪', exchange: 'SH', data_type: 'DAILY', start_date: '2020-07-20', end_date: '2026-04-18', is_full_history: false, last_sync_at: '2026-03-15T10:00:00' },
        { symbol: '000001.SZ', name: '平安银行', exchange: 'SZ', data_type: 'FINANCE', start_date: '1991-04-03', end_date: '2024-12-31', is_full_history: false, last_sync_at: '2026-01-10T09:00:00' },
      ]
      const filtered = all.filter(i =>
        (!query.symbol || i.symbol.includes(query.symbol)) &&
        (!query.data_type || i.data_type === query.data_type)
      )
      return {
        code: 0,
        message: 'ok',
        data: {
          list: filtered,
          total: filtered.length,
          page: Number(query.page ?? 1),
          page_size: Number(query.page_size ?? 10),
        },
      }
    },
  },
  {
    url: '/api/v1/coverage/:symbol',
    method: 'get',
    response: ({ params }: any) => ({
      code: 0,
      message: 'ok',
      data: {
        symbol: params.symbol,
        name: '贵州茅台',
        coverages: [
          { data_type: 'DAILY', start_date: '2001-08-27', end_date: '2026-04-18', is_full_history: true, last_sync_at: '2026-04-18T08:30:00' },
          { data_type: 'FINANCE', start_date: '2001-12-31', end_date: '2025-12-31', is_full_history: true, last_sync_at: '2026-04-18T09:00:00' },
          { data_type: 'ADJUST_FACTOR', start_date: '2001-08-27', end_date: '2026-04-18', is_full_history: true, last_sync_at: '2026-04-18T07:00:00' },
        ],
      },
    }),
  },
]
