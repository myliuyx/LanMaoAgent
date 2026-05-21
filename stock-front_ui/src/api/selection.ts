import request from './request'
import type { SelectionFilters, SelectionQueryRequest, SelectionItem, SelectionTopItem } from '@/types/selection'
import type { PageResponse } from '@/types/common'

export const selectionApi = {
  /** 获取可选交易日列表 */
  getDates: (params?: { start_date?: string; end_date?: string; limit?: number }) =>
    request.get<string[]>('/selection/dates', { params }),

  /** 获取可选行业列表 */
  getIndustries: () =>
    request.get<string[]>('/selection/industries'),

  /** 查询选股结果 */
  query: (req: SelectionQueryRequest) =>
    request.post<PageResponse<SelectionItem>>('/selection/query', req),

  /** 导出选股结果 */
  export: (req: SelectionQueryRequest) =>
    request.post<Blob>('/selection/export', req, { responseType: 'blob' }),

  /** 选股Top榜 */
  getTop: (days = 5, limit = 10) =>
    request.get<SelectionTopItem[]>('/selection/top', { params: { days, limit } }),
}
