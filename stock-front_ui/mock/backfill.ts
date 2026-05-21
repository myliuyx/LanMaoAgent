export default [
  {
    url: '/api/v1/backfill/run',
    method: 'post',
    response: () => ({
      code: 0,
      message: 'ok',
      data: { task_id: 12345, job_name: '日线数据同步', status: 'PENDING' },
    }),
  },
  {
    url: '/api/v1/backfill/status/:taskId',
    method: 'get',
    response: ({ params }: any) => {
      const id = Number(params.taskId)
      // 模拟进度
      if (id === 99999) {
        return {
          code: 0,
          message: 'ok',
          data: { task_id: id, job_name: '日线数据同步', status: 'SUCCESS', progress: 100, message: '补数任务执行成功' },
        }
      }
      return {
        code: 0,
        message: 'ok',
        data: { task_id: id, job_name: '日线数据同步', status: 'RUNNING', progress: 65, message: '正在拉取 K 线数据，已处理 65%' },
      }
    },
  },
]
