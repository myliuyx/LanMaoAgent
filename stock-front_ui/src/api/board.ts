import request from './request'
import type { PageResponse } from '@/types/common'
import type { BoardItem, BoardDetail, BoardMember } from '@/types/board'

export interface BoardListParams {
  board_type?: string
  keyword?: string
  page?: number
  page_size?: number
}

export const boardApi = {
  getList: (params?: BoardListParams, signal?: AbortSignal) =>
    request.get<PageResponse<BoardItem>>('/boards', { params, signal }),

  getDetail: (boardCode: string, signal?: AbortSignal) =>
    request.get<BoardDetail>(`/boards/${boardCode}`, { signal }),

  getMembers: (
    boardCode: string,
    params?: { page?: number; page_size?: number; sort_by?: string; sort_order?: string; signal?: AbortSignal }
  ) => request.get<PageResponse<BoardMember>>(`/boards/${boardCode}/members`, { params }),
}
