import request from './request'
import type { JobItem } from '@/types/job'
import type {
  DashboardSummary,
  CoverageSummary,
  WatchlistAnalysisResult,
} from '@/types/dashboard'

export const dashboardApi = {
  getSummary: (signal?: AbortSignal) => request.get<DashboardSummary>('/dashboard/summary', { signal }),

  getJobs: (limit = 10, signal?: AbortSignal) =>
    request.get<JobItem[]>('/dashboard/jobs', { params: { limit }, signal }),

  getCoverage: (signal?: AbortSignal) => request.get<CoverageSummary>('/dashboard/coverage', { signal }),

  getWatchlistAnalysis: (symbols: string[], signal?: AbortSignal) =>
    request.post<WatchlistAnalysisResult>('/dashboard/watchlist-analysis', { symbols }, { signal }),
}
