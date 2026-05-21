import axios, { type AxiosRequestConfig } from 'axios'
import type { ApiResponse } from '@/types/common'
import { ElMessage } from 'element-plus'
import router from '@/router'

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
})

axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

axiosInstance.interceptors.response.use(
  (response) => {
    const data = response.data
    // 检查业务错误码（非 0 都是错误）
    if (data && typeof data.code === 'number' && data.code !== 0) {
      // 业务错误码，统一抛出，由调用方 catch 处理
      const err = new Error(data.message || '请求失败') as any
      err.response = response
      err.isBusinessError = true
      err.businessCode = data.code
      return Promise.reject(err)
    }
    return response.data
  },
  (error) => {
    if (error.isBusinessError) {
      // 业务错误（上面已处理过），直接抛出，不弹 toast
      return Promise.reject(error)
    }
    if (error.response) {
      const { status, data } = error.response
      if (status === 401) {
        ElMessage.error('登录已过期，请重新登录')
        localStorage.removeItem('token')
        router.push('/login')
      } else if (status === 403) {
        ElMessage.error('权限不足')
      } else if (status >= 500) {
        ElMessage.error('服务器错误')
      } else {
        ElMessage.error(data?.message || '请求失败')
      }
    } else {
      ElMessage.error('网络错误')
    }
    return Promise.reject(error)
  }
)

const request = {
  /**
   * GET 请求。axios 拦截器返回 response.data（后端返回的 {code, message, data} 结构）。
   * 例如：get<string[]>('/dates') → Promise<ApiResponse<string[]>>
   */
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return axiosInstance.get(url, config) as Promise<ApiResponse<T>>
  },
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return axiosInstance.post(url, data, config) as Promise<ApiResponse<T>>
  },
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return axiosInstance.put(url, data, config) as Promise<ApiResponse<T>>
  },
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return axiosInstance.delete(url, config) as Promise<ApiResponse<T>>
  },
}

export default request
