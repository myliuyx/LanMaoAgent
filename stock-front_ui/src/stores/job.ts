import { defineStore } from 'pinia'
import { ref, onScopeDispose } from 'vue'
import type { JobItem } from '@/types/job'
import { jobApi } from '@/api/job'

export const useJobStore = defineStore('job', () => {
  const runningJobs = ref<JobItem[]>([])
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let visibilityHandler: (() => void) | null = null

  const fetchRunningJobs = async () => {
    try {
      const res = await jobApi.getList({ status: 'RUNNING', page_size: 20 })
      runningJobs.value = res.data?.list ?? []
    } catch {
      // 轮询错误静默处理，避免刷屏
    }
  }

  const startPolling = (intervalMs = 10000) => {
    if (pollTimer) return
    pollTimer = setInterval(fetchRunningJobs, intervalMs)
    fetchRunningJobs()

    // 页面不可见时暂停轮询，恢复时重启
    visibilityHandler = () => {
      if (document.hidden) {
        if (pollTimer) {
          clearInterval(pollTimer)
          pollTimer = null
        }
      } else {
        pollTimer = setInterval(fetchRunningJobs, intervalMs)
        fetchRunningJobs()
      }
    }
    document.addEventListener('visibilitychange', visibilityHandler)
  }

  const stopPolling = () => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    if (visibilityHandler) {
      document.removeEventListener('visibilitychange', visibilityHandler)
      visibilityHandler = null
    }
    runningJobs.value = []
  }

  onScopeDispose(() => {
    stopPolling()
  })

  return {
    runningJobs,
    fetchRunningJobs,
    startPolling,
    stopPolling,
  }
})