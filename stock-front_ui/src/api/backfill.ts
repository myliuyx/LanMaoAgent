import request from './request'

export interface BackfillRunRequest {
  symbol: string
  data_type: 'DAILY' | 'FINANCE' | 'ADJUST_FACTOR'
  start_date?: string
  end_date?: string
  force?: boolean
}

export interface BackfillStatus {
  task_id: number
  job_name: string
  status: string
  progress: number
  message: string
}

export const backfillApi = {
  run: (data: BackfillRunRequest) =>
    request.post<{ task_id: number; job_name: string; status: string }>('/backfill/run', data),

  getStatus: (taskId: number) =>
    request.get<BackfillStatus>(`/backfill/status/${taskId}`),
}
