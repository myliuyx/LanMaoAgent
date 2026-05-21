import request from './request'
import type { PageResponse } from '@/types/common'
import type { JobItem, JobQuery } from '@/types/job'

export { type JobQuery } from '@/types/job'

export const jobApi = {
  getList: (params?: JobQuery) =>
    request.get<PageResponse<JobItem>>('/jobs', { params }),

  getDetail: (jobId: number, signal?: AbortSignal) =>
    request.get<JobItem>(`/jobs/${jobId}`, { signal }),

  getLogs: (jobId: number, params?: { offset?: number; limit?: number; signal?: AbortSignal }) =>
    request.get<{ logs: string[]; total: number; offset: number; limit: number }>(
      `/jobs/${jobId}/logs`,
      { params, signal: params?.signal }
    ),

  run: (data: { job_name: string; biz_date?: string; force?: boolean }) =>
    request.post<{ task_id: number; job_name: string; status: string }>('/jobs/run', data),

  cancel: (jobId: number) =>
    request.post<{ success: boolean }>(`/jobs/${jobId}/cancel`),
}
