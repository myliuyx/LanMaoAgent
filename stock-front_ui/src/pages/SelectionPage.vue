
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElSelect, ElOption, ElButton, ElTable, ElTableColumn, ElPagination, ElTag, ElMessage, ElRadioGroup, ElRadioButton, ElEmpty } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { selectionApi } from '@/api/selection'
import { strategyApi } from '@/api/strategy'
import type { SelectionItem, SelectionFilters } from '@/types/selection'
import type { StrategyStockItem, Strategy } from '@/types/strategy'
import { formatPercent } from '@/utils/format'
import { useRouter } from 'vue-router'
import FilterPanel from '@/components/selection/FilterPanel.vue'
import StrategySelector from '@/components/strategy/StrategySelector.vue'

const router = useRouter()
const mode = ref<'filter' | 'strategy'>('filter')
const tradeDates = ref<string[]>([])
const industries = ref<string[]>([])
const selectedDate = ref('')
const tableData = ref<SelectionItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const loading = ref(false)
const excludeSt = ref(false)

// 策略相关
const selectedStrategy = ref('')
const strategyResult = ref<{ strategy: Strategy; items: StrategyStockItem[]; total: number } | null>(null)
const strategyLoading = ref(false)

// 当前排序列和方向
const sortBy = ref<string>('trend_score')
const sortOrder = ref<'asc' | 'desc'>('desc')

// 筛选条件
const filters = ref<SelectionFilters>({
  is_st: false,
  turnover_rate_min: undefined,
  roe_min: undefined,
  trend_score_min: undefined,
})

onMounted(async () => {
  // 并行请求交易日和行业列表
  const [datesRes, industriesRes] = await Promise.all([
    selectionApi.getDates({ end_date: new Date().toISOString().slice(0, 10), limit: 100 }),
    selectionApi.getIndustries(),
  ])
  tradeDates.value = datesRes.data ?? []
  industries.value = industriesRes.data ?? []
  if (tradeDates.value.length > 0) {
    // 优先选最近的历史日期（<= 今天），没有则选最近的未来日期
    const today = new Date().toISOString().slice(0, 10)
    const pastDates = tradeDates.value.filter(d => d <= today)
    selectedDate.value = pastDates.length > 0 ? pastDates[0] : tradeDates.value[tradeDates.value.length - 1]
    fetchData()
  }
})

const exportLoading = ref(false)

async function handleExport() {
  if (!selectedDate.value) {
    ElMessage.warning('请先选择交易日')
    return
  }
  exportLoading.value = true
  try {
    const res = await selectionApi.export({
      trade_date: selectedDate.value,
      filters: filters.value,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
    })
    const blob = res.data instanceof Blob ? res.data : new Blob([res.data as any], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `selection_${selectedDate.value}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败，请重试')
  } finally {
    exportLoading.value = false
  }
}

async function fetchData() {
  if (!selectedDate.value) return
  loading.value = true
  try {
    const res = await selectionApi.query({
      trade_date: selectedDate.value,
      filters: filters.value,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
      page: page.value,
      page_size: pageSize.value,
    })
    tableData.value = res.data?.list ?? []
    total.value = res.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

async function fetchStrategyData() {
  if (!selectedDate.value || !selectedStrategy.value) return
  strategyLoading.value = true
  try {
    const res = await strategyApi.queryStrategy({
      strategy_id: selectedStrategy.value,
      trade_date: selectedDate.value,
      limit: pageSize.value,
      page: page.value,
    })
    strategyResult.value = res.data ?? null
    total.value = strategyResult.value?.total ?? 0
  } catch {
    ElMessage.error('策略查询失败，请重试')
  } finally {
    strategyLoading.value = false
  }
}

const handleSearch = () => {
  page.value = 1
  // excludeSt=true → 只要非ST → is_st=false；excludeSt=false → 不过滤 → is_st=undefined
  filters.value.is_st = excludeSt.value ? false : undefined
  fetchData()
}

const handlePageChange = (p: number) => {
  page.value = p
  fetchData()
}

const handlePageChangeStrategy = (p: number) => {
  page.value = p
  fetchStrategyData()
}

const handleReset = () => {
  filters.value = {
    is_st: false,
    turnover_rate_min: undefined,
    roe_min: undefined,
    trend_score_min: undefined,
    industry_l1: undefined,
  }
  excludeSt.value = false
  sortBy.value = 'trend_score'
  sortOrder.value = 'desc'
  page.value = 1
  fetchData()
}

const handleModeChange = (newMode: string | number | boolean | undefined) => {
  if (!newMode) return
  mode.value = newMode as 'filter' | 'strategy'
  page.value = 1
  if (mode.value === 'filter') {
    strategyResult.value = null
    fetchData()
  } else if (selectedStrategy.value) {
    fetchStrategyData()
  }
}

const handleStrategyChange = (strategyId: string) => {
  page.value = 1
  if (strategyId) fetchStrategyData()
}

/** 点击列头排序 */
const handleSortChange = ({ prop, order }: { prop: string; order: string }) => {
  sortBy.value = prop || 'trend_score'
  sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  fetchData()
}

const goToStockDetail = (symbol: string) => {
  router.push(`/stocks/${symbol}`)
}
</script>
<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-header__title">选股工作台</h1>
        <p class="page-header__sub">基于趋势评分、换手率、财务指标的多维度选股</p>
      </div>
    </div>

    <!-- 模式切换 + 策略选择 -->
    <div class="mode-bar">
      <el-radio-group v-model="mode" size="default" @change="handleModeChange">
        <el-radio-button value="filter">筛选模式</el-radio-button>
        <el-radio-button value="strategy">策略模式</el-radio-button>
      </el-radio-group>

      <div v-if="mode === 'strategy'" class="mode-bar__strategy">
        <StrategySelector
          v-model="selectedStrategy"
          :trade-date="selectedDate"
          :trade-dates="tradeDates"
          @change="handleStrategyChange"
        />
        <el-button
          v-if="selectedStrategy"
          type="primary"
          size="default"
          :loading="strategyLoading"
          @click="fetchStrategyData"
        >
          执行策略
        </el-button>
      </div>
    </div>

    <!-- 筛选条件（仅筛选模式显示） -->
    <FilterPanel
      v-if="mode === 'filter'"
      v-model:filters="filters"
      v-model:trade-date="selectedDate"
      :trade-dates="tradeDates"
      :industries="industries"
      @search="handleSearch"
    />

    <!-- 策略结果表格 -->
    <div v-if="mode === 'strategy' && strategyResult" class="strategy-info-bar">
      <span class="strategy-info-bar__name">{{ strategyResult.strategy.name }}</span>
      <span class="strategy-info-bar__desc">{{ strategyResult.strategy.description }}</span>
    </div>

    <!-- 结果表格 -->
    <div class="page-card result-card">
      <div class="result-header">
        <div class="result-header__left">
          <span class="result-count">共找到 <strong>{{ total }}</strong> 只符合条件的股票</span>
        </div>
        <el-button type="success" size="small" :loading="exportLoading" @click="handleExport">
          <el-icon><Download /></el-icon><span style="margin-left:4px">导出 CSV</span>
        </el-button>
      </div>

      <!-- 筛选模式表格 -->
      <el-table
        v-if="mode === 'filter'"
        border
        style="width: 100%; table-layout: fixed"
        :data="tableData"
        stripe
        :loading="loading"
        row-class-name="clickable-row"
        @sort-change="handleSortChange"
        @row-click="(row) => goToStockDetail(row.symbol)"
      >
        <el-table-column prop="symbol" label="代码" width="110" sortable="custom" />
        <el-table-column prop="name" label="名称" min-width="120" show-overflow-tooltip />
        <el-table-column prop="exchange" label="交易所" width="70">
          <template #default="{ row }">{{ row.exchange === 'SH' ? '上交所' : '深交所' }}</template>
        </el-table-column>
        <el-table-column prop="industry_l1" label="行业" min-width="120" show-overflow-tooltip />
        <el-table-column prop="close" label="收盘价" width="100" align="right" sortable="custom">
          <template #default="{ row }">{{ row.close?.toFixed(2) ?? '-' }}</template>
        </el-table-column>
        <el-table-column prop="change_pct" label="涨跌幅" width="100" align="right" sortable="custom">
          <template #default="{ row }">
            <span :class="row.change_pct > 0 ? 'text-rise' : row.change_pct < 0 ? 'text-fall' : 'text-flat'">
              {{ formatPercent(row.change_pct) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="turnover_rate" label="换手率" width="90" align="right" sortable="custom">
          <template #default="{ row }">{{ formatPercent(row.turnover_rate) }}</template>
        </el-table-column>
        <el-table-column prop="pct_change_5d" label="5日涨幅" width="100" align="right" sortable="custom">
          <template #default="{ row }">
            <span :class="row.pct_change_5d > 0 ? 'text-rise' : row.pct_change_5d < 0 ? 'text-fall' : 'text-flat'">
              {{ formatPercent(row.pct_change_5d) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="pct_change_20d" label="20日涨幅" width="110" align="right" sortable="custom">
          <template #default="{ row }">
            <span :class="row.pct_change_20d > 0 ? 'text-rise' : row.pct_change_20d < 0 ? 'text-fall' : 'text-flat'">
              {{ formatPercent(row.pct_change_20d) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="trend_score" label="趋势评分" width="100" align="right" sortable="custom">
          <template #default="{ row }">
            <el-tag v-if="row.trend_score >= 80" type="success" size="small" effect="plain">{{ row.trend_score }}</el-tag>
            <el-tag v-else-if="row.trend_score >= 60" type="warning" size="small" effect="plain">{{ row.trend_score }}</el-tag>
            <span v-else>{{ row.trend_score }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_new" label="次新" width="70" align="center">
          <template #default="{ row }"><el-tag v-if="row.is_new" type="primary" size="small" effect="plain">次新</el-tag><span v-else>-</span></template>
        </el-table-column>
      </el-table>

      <!-- 策略模式表格 -->
      <el-table
        v-if="mode === 'strategy' && strategyResult"
        border
        style="width: 100%; table-layout: fixed"
        :data="strategyResult.items"
        stripe
        :loading="strategyLoading"
        row-class-name="clickable-row"
        @row-click="(row) => goToStockDetail(row.symbol)"
      >
        <el-table-column prop="symbol" label="代码" width="110" />
        <el-table-column prop="name" label="名称" min-width="120" show-overflow-tooltip />
        <el-table-column prop="exchange" label="交易所" width="70">
          <template #default="{ row }">{{ row.exchange === 'SH' ? '上交所' : '深交所' }}</template>
        </el-table-column>
        <el-table-column prop="close" label="收盘价" width="100" align="right">
          <template #default="{ row }">{{ row.close?.toFixed(2) ?? '-' }}</template>
        </el-table-column>
        <el-table-column prop="change_pct" label="涨跌幅" width="100" align="right">
          <template #default="{ row }">
            <span :class="row.change_pct > 0 ? 'text-rise' : row.change_pct < 0 ? 'text-fall' : 'text-flat'">
              {{ formatPercent(row.change_pct) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="turnover_rate" label="换手率" width="90" align="right">
          <template #default="{ row }">{{ formatPercent(row.turnover_rate) }}</template>
        </el-table-column>
        <el-table-column prop="score" label="策略评分" width="100" align="right">
          <template #default="{ row }">
            <el-tag v-if="row.score >= 80" type="success" size="small" effect="plain">{{ row.score }}</el-tag>
            <el-tag v-else-if="row.score >= 60" type="warning" size="small" effect="plain">{{ row.score }}</el-tag>
            <span v-else>{{ row.score }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="match_reason" label="匹配原因" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.match_reason }}</template>
        </el-table-column>
        <el-table-column label="信号" width="180">
          <template #default="{ row }">
            <div style="display: flex; flex-wrap: wrap; gap: 2px;">
              <el-tag
                v-for="sig in row.signals"
                :key="sig.name"
                size="small"
                effect="plain"
              >
                {{ sig.name }}:{{ sig.value }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 策略模式空状态 -->
      <el-empty
        v-if="mode === 'strategy' && !strategyResult && !strategyLoading"
        description="请先选择策略，然后点击「执行策略」"
      />

      <!-- 分页 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @current-change="mode === 'filter' ? handlePageChange(page) : handlePageChangeStrategy(page)"
          @size-change="mode === 'filter' ? (() => { page = 1; fetchData() })() : (() => { page = 1; fetchStrategyData() })()"
        />
      </div>
    </div>
  </div>
</template>
<style scoped>
:deep(.clickable-row) {
  cursor: pointer;
}

/* ── 筛选卡片 ─────────────────────────────────────────── */
.filter-card {
  margin-bottom: 16px;
}

.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.filter-header__left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-body {
  padding: 16px 20px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 14px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.filter-actions {
  display: flex;
  gap: 8px;
}

/* ── 结果卡片 ─────────────────────────────────────────── */
.result-card {
  overflow: visible;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid #f1f5f9;
}

.result-count {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.result-count strong {
  color: var(--color-primary);
  font-weight: 700;
}

/* ── 分页 ─────────────────────────────────────────────── */
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 14px 16px;
  border-top: 1px solid #f1f5f9;
}

/* ── 行可点击 ─────────────────────────────────────────── */
.clickable-row {
  cursor: pointer;
}

/* ── 模式切换栏 ─────────────────────────────────────────── */
.mode-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  margin-bottom: 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.mode-bar__strategy {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ── 策略信息栏 ─────────────────────────────────────────── */
.strategy-info-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  margin-bottom: 8px;
  background: var(--el-color-success-light-9);
  border-radius: 6px;
  font-size: 13px;
}

.strategy-info-bar__name {
  font-weight: 600;
  color: var(--el-color-success);
}

.strategy-info-bar__desc {
  color: var(--el-color-info);
}

</style>