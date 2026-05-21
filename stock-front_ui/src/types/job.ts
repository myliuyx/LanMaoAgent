// 任务状态枚举
export type JobStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'CANCELLED' | 'PARTIAL'

// 任务项
export interface JobItem {
  id: number
  job_name: string
  biz_date: string | null
  status: JobStatus
  start_time: string
  end_time: string | null
  duration_ms: number | null
  rows_raw: number | null
  rows_written: number | null
  error_message: string | null
}

// 任务查询参数
export interface JobQuery {
  job_name?: string
  status?: JobStatus | ''
  biz_date?: string
  page?: number
  page_size?: number
  signal?: AbortSignal
}

// 触发任务请求
export interface RunJobRequest {
  job_name: string
  biz_date?: string
  force?: boolean
  params?: Record<string, unknown>
}
