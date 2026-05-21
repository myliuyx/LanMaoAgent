<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElCard, ElTag } from 'element-plus'
import { dashboardApi } from '@/api/dashboard'
import type { DashboardSummary, CoverageSummary, WatchlistAnalysisResult } from '@/types/dashboard'
import { selectionApi } from '@/api/selection'
import type { SelectionTopItem } from '@/types/selection'
import { watchlistApi } from '@/api/watchlist'
import type { JobItem } from '@/types/job'
import { fmtCount } from '@/utils/format'
import BaseStatCard from '@/components/base/BaseStatCard.vue'
import RecentJobsCard from '@/components/dashboard/RecentJobsCard.vue'
import CoverageCard from '@/components/dashboard/CoverageCard.vue'
import WatchlistAnalysisCard from '@/components/dashboard/WatchlistAnalysisCard.vue'
import SelectionTopCard from '@/components/dashboard/SelectionTopCard.vue'

const summary = ref<DashboardSummary | null>(null)
const jobs = ref<JobItem[]>([])
const coverage = ref<CoverageSummary | null>(null)
const loading = ref(false)

const watchlistAnalysis = ref<WatchlistAnalysisResult | null>(null)
const watchlistLoading = ref(false)

const selectionTop = ref<SelectionTopItem[]>([])
const selectionTopLoading = ref(false)

onMounted(() => {
  fetchAll()
})

async function fetchAll() {
  loading.value = true
  try {
    const [summaryRes, jobsRes, coverageRes] = await Promise.all([
      dashboardApi.getSummary(),
      dashboardApi.getJobs(10),
      dashboardApi.getCoverage(),
    ])
    summary.value = summaryRes.data ?? null
    jobs.value = jobsRes.data ?? []
    coverage.value = coverageRes.data ?? null

    await Promise.all([fetchWatchlistAnalysis(), fetchSelectionTop()])
  } catch (e) {
    console.error('加载仪表盘失败', e)
  } finally {
    loading.value = false
  }
}

async function fetchWatchlistAnalysis() {
  watchlistLoading.value = true
  try {
    const wlRes = await watchlistApi.getList({ page: 1, page_size: 100 })
    const list = wlRes.data?.list ?? []

    const savedOrder = (() => {
      try {
        const raw = localStorage.getItem('watchlist-order')
        return raw ? JSON.parse(raw) : []
      } catch { return [] }
    })()
    const orderMap = new Map(savedOrder.map((s: string, i: number) => [s, i]))
    const sortedList = [...list].sort((a: any, b: any) => {
      const ai = orderMap.get(a.symbol) as number | undefined
      const bi = orderMap.get(b.symbol) as number | undefined
      return (ai ?? Infinity) - (bi ?? Infinity)
    })

    const symbols = sortedList.map((item: any) => item.symbol)
    if (symbols.length > 0) {
      const analysisRes = await dashboardApi.getWatchlistAnalysis(symbols)
      watchlistAnalysis.value = analysisRes.data ?? null
    }
  } catch (e) {
    console.error('加载自选股分析失败', e)
  } finally {
    watchlistLoading.value = false
  }
}

async function fetchSelectionTop() {
  selectionTopLoading.value = true
  try {
    const res = await selectionApi.getTop(5, 10)
    selectionTop.value = res.data ?? []
  } catch (e) {
    console.error('加载选股Top榜失败', e)
  } finally {
    selectionTopLoading.value = false
  }
}
</script>

<template>
  <div class="dashboard-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header__left">
        <h1 class="page-title">数据看板</h1>
        <el-tag v-if="summary" :type="summary.is_trade_day ? 'success' : 'info'" size="small">
          {{ summary.is_trade_day ? '交易日' : '非交易日' }}
        </el-tag>
      </div>
      <div class="page-header__right">
        <span class="page-header__date" v-if="summary">
          最新交易日：{{ summary.latest_trade_date }}
        </span>
      </div>
    </div>

    <!-- 概览卡片 -->
    <div class="stats-grid">
      <BaseStatCard
        title="股票总数"
        :value="summary?.stock_count ?? '-'"
        suffix="只"
        :loading="loading"
      />
      <BaseStatCard
        title="日线数据"
        :value="fmtCount(summary?.daily_record_count)"
        :loading="loading"
      />
      <BaseStatCard
        title="财务数据"
        :value="fmtCount(summary?.finance_record_count)"
        :loading="loading"
      />
      <BaseStatCard
        title="技术因子"
        :value="fmtCount(summary?.factor_record_count)"
        :loading="loading"
      />
    </div>

    <!-- 中间两栏 -->
    <div class="mid-grid">
      <RecentJobsCard :jobs="jobs" :loading="loading" />
      <CoverageCard :coverage="coverage" :loading="loading" />
    </div>

    <!-- 自选股分析 + 选股Top榜 -->
    <div class="mid-grid">
      <WatchlistAnalysisCard :watchlist-analysis="watchlistAnalysis" :watchlist-loading="watchlistLoading" />
      <SelectionTopCard :selection-top="selectionTop" :selection-top-loading="selectionTopLoading" />
    </div>
  </div>
</template>

<style scoped>
.dashboard-page {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-header__left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.page-header__date {
  font-size: 13px;
  color: var(--color-text-muted);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.mid-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
</style>