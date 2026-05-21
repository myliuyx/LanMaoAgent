export default [
  {
    url: '/api/v1/dashboard/summary',
    method: 'get',
    response: () => ({
      code: 0,
      message: 'ok',
      data: {
        latest_trade_date: '2026-04-18',
        is_trade_day: true,
        stock_count: 5200,
        daily_record_count: 1256800,
        finance_record_count: 89600,
        factor_record_count: 312000,
        today_job_success_count: 8,
        today_job_failed_count: 1,
        selection_count: 42,
      },
    }),
  },
  {
    url: '/api/v1/dashboard/jobs',
    method: 'get',
    response: () => ({
      code: 0,
      message: 'ok',
      data: [
        { id: 101, job_name: '日线数据同步', biz_date: '2026-04-18', status: 'SUCCESS', start_time: '2026-04-18T08:00:00', end_time: '2026-04-18T08:12:33', duration_ms: 753000, rows_raw: 1256800, rows_written: 1256800, error_message: null },
        { id: 102, job_name: '财务数据更新', biz_date: '2026-04-17', status: 'SUCCESS', start_time: '2026-04-18T07:30:00', end_time: '2026-04-18T07:45:12', duration_ms: 912000, rows_raw: 89600, rows_written: 89600, error_message: null },
        { id: 103, job_name: '指数成分股同步', biz_date: '2026-04-18', status: 'FAILED', start_time: '2026-04-18T09:00:00', end_time: '2026-04-18T09:05:00', duration_ms: 300000, rows_raw: 12000, rows_written: 0, error_message: '网络超时，无法连接数据源' },
      ],
    }),
  },
  {
    url: '/api/v1/dashboard/coverage',
    method: 'get',
    response: () => ({
      code: 0,
      message: 'ok',
      data: {
        stocks_with_full_daily: 4980,
        stocks_with_full_finance: 4200,
        stocks_need_backfill: 156,
        total_stocks: 5200,
      },
    }),
  },
]
