// 通用 API 响应结构
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

// 分页响应结构
export interface PageResponse<T> {
  list: T[]
  page: number
  page_size: number
  total: number
}

// 登录响应
export interface LoginResponse {
  token: string
  expires_in: number
  user: {
    id: number
    username: string
    role: string
  }
}
