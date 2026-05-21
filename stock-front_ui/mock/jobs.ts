export default [
  {
    url: '/api/v1/jobs',
    method: 'get',
    response: ({ query }: any) => {
      const all = [
        { id: 101, job_name: '日线数据同步', biz_date: '2026-04-18', status: 'SUCCESS', start_time: '2026-04-18T08:00:00', end_time: '2026-04-18T08:12:33', duration_ms: 753000, rows_raw: 1256800, rows_written: 1256800, error_message: null },
        { id: 102, job_name: '财务数据更新', biz_date: '2026-04-17', status: 'SUCCESS', start_time: '2026-04-18T07:30:00', end_time: '2026-04-18T07:45:12', duration_ms: 912000, rows_raw: 89600, rows_written: 89600, error_message: null },
        { id: 103, job_name: '指数成分股同步', biz_date: '2026-04-18', status: 'FAILED', start_time: '2026-04-18T09:00:00', end_time: '2026-04-18T09:05:00', duration_ms: 300000, rows_raw: 12000, rows_written: 0, error_message: '网络超时，无法连接数据源' },
        { id: 104, job_name: '北向资金数据', biz_date: '2026-04-18', status: 'RUNNING', start_time: '2026-04-18T10:00:00', end_time: null, duration_ms: null, rows_raw: null, rows_written: null, error_message: null },
        { id: 105, job_name: '复权因子更新', biz_date: '2026-04-17', status: 'SUCCESS', start_time: '2026-04-18T06:00:00', end_time: '2026-04-18T06:28:45', duration_ms: 1725000, rows_raw: 5200, rows_written: 5200, error_message: null },
        { id: 106, job_name: '板块关联更新', biz_date: '2026-04-17', status: 'PENDING', start_time: null, end_time: null, duration_ms: null, rows_raw: null, rows_written: null, error_message: null },
      ]
      const filtered = all.filter(j =>
        (!query.status || query.status === '' || j.status === query.status) &&
        (!query.job_name || j.job_name.includes(query.job_name))
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
    url: '/api/v1/jobs/:id',
    method: 'get',
    response: ({ params }: any) => ({
      code: 0,
      message: 'ok',
      data: { id: Number(params.id), job_name: '日线数据同步', biz_date: '2026-04-18', status: 'SUCCESS', start_time: '2026-04-18T08:00:00', end_time: '2026-04-18T08:12:33', duration_ms: 753000, rows_raw: 1256800, rows_written: 1256800, error_message: null },
    }),
  },
  {
    url: '/api/v1/jobs/:id/logs',
    method: 'get',
    response: ({ params, query }: any) => {
      const lines = [
        `[08:00:01] INFO - 任务启动: 日线数据同步, 业务日期: 2026-04-18`,
        `[08:00:02] INFO - 开始连接数据源: ws://market-data-api/v1/daily`,
        `[08:00:05] INFO - 连接成功, 开始拉取全市场股票列表`,
        `[08:00:08] INFO - 共获取 5200 只股票, 开始分批推送 K 线数据`,
        `[08:01:30] INFO - 已处理 1000/5200 只股票, 当前进度 19.2%`,
        `[08:03:15] INFO - 已处理 2500/5200 只股票, 当前进度 48.1%`,
        `[08:05:02] INFO - 已处理 4000/5200 只股票, 当前进度 76.9%`,
        `[08:07:45] INFO - 已处理 5000/5200 只股票, 当前进度 96.2%`,
        `[08:08:22] WARN - 股票 600026.SH 停牌, 跳过`,
        `[08:08:30] INFO - 数据写入完成, 共写入 1256800 条记录`,
        `[08:08:31] INFO - 任务成功结束, 耗时 753 秒`,
      ]
      const offset = Number(query.offset ?? 0)
      const limit = Number(query.limit ?? 100)
      const slice = lines.slice(offset, offset + limit)
      return {
        code: 0,
        message: 'ok',
        data: { logs: slice, total: lines.length, offset, limit },
      }
    },
  },
  {
    url: '/api/v1/jobs/run',
    method: 'post',
    response: () => ({
      code: 0,
      message: 'ok',
      data: { task_id: 99999, job_name: '日线数据同步', status: 'PENDING' },
    }),
  },
  {
    url: '/api/v1/jobs/:id/cancel',
    method: 'post',
    response: () => ({
      code: 0,
      message: 'ok',
      data: { success: true },
    }),
  },
]
