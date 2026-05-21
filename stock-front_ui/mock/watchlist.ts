export default [
  // 获取自选股列表
  {
    url: '/api/v1/watchlist',
    method: 'get',
    response: () => ({
      code: 0,
      message: 'success',
      data: {
        list: [
          {
            symbol: '600519.SH',
            name: '贵州茅台',
            exchange: 'SH',
            added_at: '2026-04-18T10:00:00+08:00',
            close: 1800.0,
            change_pct: 1.25,
            turnover_rate: 0.85,
            trend_score: 100.0,
          },
          {
            symbol: '000858.SZ',
            name: '五粮液',
            exchange: 'SZ',
            added_at: '2026-04-17T14:30:00+08:00',
            close: 168.5,
            change_pct: -0.5,
            turnover_rate: 1.2,
            trend_score: 85.5,
          },
          {
            symbol: '300750.SZ',
            name: '宁德时代',
            exchange: 'SZ',
            added_at: '2026-04-15T09:00:00+08:00',
            close: 520.0,
            change_pct: 2.3,
            turnover_rate: 2.1,
            trend_score: 78.0,
          },
        ],
        page: 1,
        page_size: 50,
        total: 3,
      },
    }),
  },

  // 添加自选
  {
    url: '/api/v1/watchlist',
    method: 'post',
    response: ({ body }: any) => ({
      code: 0,
      message: '添加成功',
      data: {
        symbol: body?.symbol,
        added_at: new Date().toISOString(),
      },
    }),
  },

  // 删除自选
  {
    url: '/api/v1/watchlist/:symbol',
    method: 'delete',
    response: () => ({
      code: 0,
      message: '删除成功',
      data: null,
    }),
  },

  // 检查是否在自选
  {
    url: '/api/v1/watchlist/check/:symbol',
    method: 'get',
    response: ({ params }: any) => ({
      code: 0,
      message: 'success',
      data: {
        symbol: params?.symbol,
        in_watchlist: false,
      },
    }),
  },
]