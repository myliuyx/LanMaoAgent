export default [
  {
    url: '/api/v1/boards',
    method: 'get',
    response: ({ query }: any) => {
      const all = [
        { board_code: 'BK0001', board_name: '白酒行业', board_type: 'INDUSTRY', stock_count: 20, is_active: true },
        { board_code: 'BK0002', board_name: '锂电池', board_type: 'INDUSTRY', stock_count: 156, is_active: true },
        { board_code: 'BK0003', board_name: '半导体', board_type: 'INDUSTRY', stock_count: 238, is_active: true },
        { board_code: 'BK0004', board_name: '上证50成分', board_type: 'INDEX_CONST', stock_count: 50, is_active: true },
        { board_code: 'BK0005', board_name: '超级品牌', board_type: 'CONCEPT', stock_count: 42, is_active: true },
        { board_code: 'BK0006', board_name: '医疗器械', board_type: 'INDUSTRY', stock_count: 98, is_active: true },
        { board_code: 'BK0007', board_name: '光伏设备', board_type: 'INDUSTRY', stock_count: 67, is_active: true },
        { board_code: 'BK0008', board_name: '宁德时代概念', board_type: 'CONCEPT', stock_count: 89, is_active: true },
      ]
      const filtered = all.filter(b =>
        (!query.keyword || b.board_name.includes(query.keyword)) &&
        (!query.board_type || query.board_type === '' || b.board_type === query.board_type)
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
    url: '/api/v1/boards/:code',
    method: 'get',
    response: ({ params }: any) => ({
      code: 0,
      message: 'ok',
      data: {
        board_code: params.code,
        board_name: '白酒行业',
        board_type: 'INDUSTRY',
        parent_board_code: null,
        is_active: true,
      },
    }),
  },
  {
    url: '/api/v1/boards/:code/members',
    method: 'get',
    response: ({ params, query }: any) => ({
      code: 0,
      message: 'ok',
      data: {
        list: [
          { symbol: '600519.SH', name: '贵州茅台', exchange: 'SH', weight: 18.5, pct_change: 3.25, is_st: false },
          { symbol: '000858.SZ', name: '五粮液', exchange: 'SZ', weight: 12.3, pct_change: 2.18, is_st: false },
          { symbol: '000568.SZ', name: '泸州老窖', exchange: 'SZ', weight: 8.7, pct_change: 1.56, is_st: false },
          { symbol: '002304.SZ', name: '洋河股份', exchange: 'SZ', weight: 7.2, pct_change: 0.89, is_st: false },
          { symbol: '600199.SH', name: '金种子酒', exchange: 'SH', weight: 3.1, pct_change: -0.45, is_st: false },
        ],
        total: 20,
        page: Number(query.page ?? 1),
        page_size: Number(query.page_size ?? 10),
      },
    }),
  },
]
