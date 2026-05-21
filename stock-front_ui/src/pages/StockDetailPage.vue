<script setup lang="ts">
import { ref, watch, computed, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  ElCard, ElTable, ElTableColumn, ElTag,
  ElRadioGroup, ElRadioButton, ElPagination, ElEmpty, ElIcon,
} from 'element-plus'
import { TrendCharts, Money, Timer } from '@element-plus/icons-vue'
import { stockApi } from '@/api/stock'
import { watchlistApi } from '@/api/watchlist'
import { ElMessage } from 'element-plus'
import KLineChart from '@/components/stock/KLineChart.vue'
import VolumeChart from '@/components/stock/VolumeChart.vue'
import StockHeader from '@/components/stock/StockHeader.vue'
import StockQuickStats from '@/components/stock/StockQuickStats.vue'
import StockInfoGrid from '@/components/stock/StockInfoGrid.vue'
import StockBoardsSection from '@/components/stock/StockBoardsSection.vue'
import type {
  StockProfile, StockDaily, StockFactor,
  FinancialIndicator, StockBoard, DataCoverage,
} from '@/types/stock'
import { formatDate, formatPercent } from '@/utils/format'
import { debounce } from '@/utils/debounce'

const route = useRoute()
const symbol = ref(route.params.symbol as string)

const DATA_TYPE_TAG_MAP: Record<string, string> = {
  DAILY: '日线',
  FINANCE: '财务',
  ADJUST_FACTOR: '复权因子',
}

const adjustType = ref<'none' | 'forward' | 'backward'>('forward')

const profile = ref<StockProfile | null>(null)
const dailyData = ref<StockDaily[]>([])
const factors = ref<StockFactor[]>([])
const financials = ref<FinancialIndicator[]>([])
const boards = ref<StockBoard[]>([])
const coverage = ref<DataCoverage[]>([])
const loading = ref(false)
const dailyPage = ref(1)
const dailyPageSize = ref(20)

// 地域（从 AREA 板块提取）
const area = ref<string | null>(null)

const klineChartRef = ref<InstanceType<typeof KLineChart> | null>(null)
const volumeChartRef = ref<InstanceType<typeof VolumeChart> | null>(null)

// 自选股状态
const inWatchlist = ref(false)
const watchlistLoading = ref(false)

// 最新行情数据
const latestDaily = computed<StockDaily | null>(() => {
  if (!dailyData.value.length) return null
  return dailyData.value[dailyData.value.length - 1]
})

// 日线行情分页数据
const dailyDataPaginated = computed(() => {
  const reversed = dailyData.value.slice().reverse()
  const start = (dailyPage.value - 1) * dailyPageSize.value
  return reversed.slice(start, start + dailyPageSize.value)
})

const dailyTotal = computed(() => dailyData.value.length)

async function fetchAll() {
  loading.value = true
  try {
    const [profileRes, factorsRes, financeRes, boardsRes, coverageRes, watchlistRes] = await Promise.all([
      stockApi.getProfile(symbol.value),
      stockApi.getFactors(symbol.value, { limit: 60 }),
      stockApi.getFinance(symbol.value),
      stockApi.getBoards(symbol.value),
      stockApi.getCoverage(symbol.value).catch(() => []),
      watchlistApi.check(symbol.value).catch(() => ({ code: -1, message: 'check failed', data: { in_watchlist: false } })),
    ])
    profile.value = profileRes.data
    factors.value = factorsRes.data ?? []
    financials.value = financeRes.data ?? []
    boards.value = boardsRes.data ?? []
    coverage.value = coverageRes ?? []
    inWatchlist.value = watchlistRes.data?.in_watchlist ?? false

    // 补充 profile 中缺失的 area 和 list_board
    if (profile.value) {
      if (!profile.value.list_board) {
        profile.value.list_board = profile.value.security_type ?? null
      }
      if (!profile.value.area) {
        const areaBoard = boards.value.find(b => b.board_type === 'AREA')
        area.value = areaBoard ? areaBoard.board_name.replace(/板块$/, '') : null
      }
    }
  } finally {
    loading.value = false
  }
}

function loadDaily() {
  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - 180)
  stockApi.getDaily(symbol.value, {
    start_date: startDate.toISOString().slice(0, 10),
    end_date: endDate.toISOString().slice(0, 10),
    limit: 120,
    adjust: adjustType.value,
  }).then(res => {
    dailyData.value = res.data ?? []
  }).catch(() => {
    // 静默忽略，错误拦截器已处理
  })
}
const fetchDaily = debounce(loadDaily, 300)

fetchAll()
fetchDaily()

const stopAdjustWatch = watch(adjustType, () => {
  fetchDaily.cancel()
  fetchDaily()
})
const stopSymbolWatch = watch(() => route.params.symbol, (newSymbol) => {
  if (newSymbol && newSymbol !== symbol.value) {
    symbol.value = newSymbol as string
    fetchDaily.cancel()
    fetchAll()
    fetchDaily()
  }
})

onUnmounted(() => {
  stopAdjustWatch()
  stopSymbolWatch()
  fetchDaily.cancel()
})

function onKlineClick(data: StockDaily) {
  const idx = dailyData.value.findIndex(d => d.trade_date === data.trade_date)
  if (idx >= 0) volumeChartRef.value?.syncCrosshair({ dataIndex: idx })
}

function onVolumeClick(_data: StockDaily) {
  // 成交量点击不做联动
}

function formatVol(v: number) {
  if (v == null || v === 0) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + ' 亿'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + ' 万'
  return String(v)
}

// 自选股切换
async function toggleWatchlist() {
  watchlistLoading.value = true
  try {
    if (inWatchlist.value) {
      await watchlistApi.remove(symbol.value)
      inWatchlist.value = false
      ElMessage.success('已从自选列表移除')
    } else {
      await watchlistApi.add(symbol.value)
      inWatchlist.value = true
      ElMessage.success('已加入自选列表')
    }
  } catch (e: any) {
    ElMessage.error(e?.message ?? '操作失败，请重试')
  } finally {
    watchlistLoading.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <!-- 个股头部 -->
    <StockHeader
      :profile="profile"
      :latest-daily="latestDaily"
      :in-watchlist="inWatchlist"
      :watchlist-loading="watchlistLoading"
      @toggle-watchlist="toggleWatchlist"
    />

    <!-- 快速指标 -->
    <StockQuickStats :latest-daily="latestDaily" />

    <!-- 基本信息 -->
    <StockInfoGrid :profile="profile" :area="area" />

    <!-- K线图 -->
    <div class="page-card page-card--flex" style="margin-bottom: 8px">
      <div class="section-header section-header--nowrap">
        <div class="section-header__left">
          <el-icon><TrendCharts /></el-icon> K线走势
        </div>
        <el-radio-group v-model="adjustType" size="small">
          <el-radio-button value="forward">前复权</el-radio-button>
          <el-radio-button value="backward">后复权</el-radio-button>
          <el-radio-button value="none">不复权</el-radio-button>
        </el-radio-group>
      </div>
      <div class="kline-wrapper">
        <KLineChart ref="klineChartRef" :data="dailyData" :height="360" :show-volume="true" :show-grid="true" @click="onKlineClick" />
      </div>
    </div>

    <!-- 成交量图 -->
    <div class="page-card" style="margin-bottom: 16px">
      <div class="section-header">
        <el-icon><Timer /></el-icon> 成交量
      </div>
      <VolumeChart ref="volumeChartRef" :data="dailyData" :height="180" :show-m-a="true" @click="onVolumeClick" />
    </div>

    <!-- 所属板块 -->
    <StockBoardsSection :boards="boards" />

    <!-- 日线行情表格 -->
    <div class="page-card" style="margin-bottom: 16px">
      <div class="section-header">日线行情</div>
      <el-table :data="dailyDataPaginated" stripe border style="width: 100%; table-layout: fixed" v-if="dailyData.length > 0">
        <el-table-column prop="trade_date" label="日期" width="140" fixed />
        <el-table-column prop="open" label="开盘" width="140" align="right"><template #default="{ row }">{{ row.open?.toFixed(2) ?? '-' }}</template></el-table-column>
        <el-table-column prop="high" label="最高" width="140" align="right"><template #default="{ row }">{{ row.high?.toFixed(2) ?? '-' }}</template></el-table-column>
        <el-table-column prop="low" label="最低" width="140" align="right"><template #default="{ row }">{{ row.low?.toFixed(2) ?? '-' }}</template></el-table-column>
        <el-table-column prop="close" label="收盘" width="140" align="right">
          <template #default="{ row }"><span :class="row.change_pct > 0 ? 'text-rise' : row.change_pct < 0 ? 'text-fall' : 'text-flat'">{{ row.close?.toFixed(2) ?? '-' }}</span></template>
        </el-table-column>
        <el-table-column prop="change_pct" label="涨跌幅" width="140" align="right">
          <template #default="{ row }"><span :class="row.change_pct > 0 ? 'text-rise' : row.change_pct < 0 ? 'text-fall' : 'text-flat'">{{ formatPercent(row.change_pct) }}</span></template>
        </el-table-column>
        <el-table-column prop="volume" label="成交量" width="150" align="right"><template #default="{ row }">{{ formatVol(row.volume) }}</template></el-table-column>
        <el-table-column prop="turnover_rate" label="换手率" min-width="130" align="right"><template #default="{ row }">{{ formatPercent(row.turnover_rate) }}</template></el-table-column>
      </el-table>
      <el-pagination
        v-if="dailyData.length > 0"
        v-model:current-page="dailyPage"
        :page-size="dailyPageSize"
        :total="dailyTotal"
        layout="prev, pager, next"
        background
        style="margin-top: 12px; justify-content: flex-end"
      />
      <el-empty v-else description="暂无数据" :image-size="60" />
    </div>

    <!-- 技术因子 -->
    <div class="page-card" style="margin-bottom: 16px">
      <div class="section-header">技术因子</div>
      <el-table :data="factors" stripe max-height="320" border style="width: 100%; table-layout: fixed" v-if="factors.length > 0">
        <el-table-column prop="trade_date" label="日期" width="140" fixed />
        <el-table-column prop="ma5" label="MA5" width="100" align="right" />
        <el-table-column prop="ma10" label="MA10" width="100" align="right" />
        <el-table-column prop="ma20" label="MA20" width="100" align="right" />
        <el-table-column prop="ma60" label="MA60" width="100" align="right" />
        <el-table-column prop="rsi_6" label="RSI6" width="95" align="right" />
        <el-table-column prop="rsi_14" label="RSI14" width="95" align="right" />
        <el-table-column prop="macd_dif" label="DIF" width="100" align="right" />
        <el-table-column prop="macd_dea" label="DEA" width="100" align="right" />
        <el-table-column prop="atr_14" label="ATR14" width="100" align="right" />
        <el-table-column prop="trend_score" label="趋势评分" width="110" align="right" />
        <el-table-column prop="is_new_high_60d" label="60日新高" width="110">
          <template #default="{ row }"><el-tag v-if="row.is_new_high_60d" type="success" size="small" effect="plain">是</el-tag><span v-else>-</span></template>
        </el-table-column>
        <el-table-column prop="is_break_ma20" label="突破MA20" min-width="90">
          <template #default="{ row }"><el-tag v-if="row.is_break_ma20" type="warning" size="small" effect="plain">是</el-tag><span v-else>-</span></template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无数据" :image-size="60" />
    </div>

    <!-- 财务指标 -->
    <div class="page-card" style="margin-bottom: 16px">
      <div class="section-header">
        <el-icon><Money /></el-icon> 财务指标
      </div>
      <el-table :data="financials" stripe border style="width: 100%; table-layout: fixed" v-if="financials.length > 0">
        <el-table-column prop="report_period" label="报告期" width="130" />
        <el-table-column prop="report_type" label="类型" width="100" />
        <el-table-column prop="eps" label="EPS" width="100" align="right" />
        <el-table-column prop="bps" label="每股净资产" width="120" align="right" />
        <el-table-column prop="roe" label="ROE" width="100" align="right"><template #default="{ row }">{{ formatPercent(row.roe) }}</template></el-table-column>
        <el-table-column prop="gross_margin" label="毛利率" width="110" align="right"><template #default="{ row }">{{ formatPercent(row.gross_margin) }}</template></el-table-column>
        <el-table-column prop="net_margin" label="净利率" width="110" align="right"><template #default="{ row }">{{ formatPercent(row.net_margin) }}</template></el-table-column>
        <el-table-column prop="revenue_yoy" label="营收同比" width="120" align="right"><template #default="{ row }">{{ formatPercent(row.revenue_yoy) }}</template></el-table-column>
        <el-table-column prop="net_profit_yoy" label="净利润同比" min-width="110" align="right"><template #default="{ row }">{{ formatPercent(row.net_profit_yoy) }}</template></el-table-column>
      </el-table>
      <el-empty v-else description="暂无数据" :image-size="60" />
    </div>

    <!-- 数据覆盖 -->
    <div class="page-card" style="margin-bottom: 16px">
      <div class="section-header">数据覆盖</div>
      <el-table :data="coverage" stripe border style="width: 100%; table-layout: fixed" v-if="coverage.length > 0">
        <el-table-column prop="data_type" label="数据类型" width="140">
          <template #default="{ row }">
            <el-tag size="small" :type="row.data_type === 'DAILY' ? 'primary' : row.data_type === 'FINANCE' ? 'success' : 'warning'" effect="plain">
              {{ DATA_TYPE_TAG_MAP[row.data_type] ?? row.data_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_date" label="开始日期" width="120"><template #default="{ row }">{{ formatDate(row.start_date ?? '') }}</template></el-table-column>
        <el-table-column prop="end_date" label="结束日期" width="120"><template #default="{ row }">{{ formatDate(row.end_date ?? '') }}</template></el-table-column>
        <el-table-column prop="is_full_history" label="全历史" width="100">
          <template #default="{ row }"><el-tag :type="row.is_full_history ? 'success' : 'info'" size="small" effect="plain">{{ row.is_full_history ? '是' : '否' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="last_sync_at" label="最后同步"><template #default="{ row }">{{ row.last_sync_at ? formatDate(row.last_sync_at) : '-' }}</template></el-table-column>
      </el-table>
      <el-empty v-else description="暂无数据覆盖信息" :image-size="60" />
    </div>
  </div>
</template>

<style scoped>
.page-card {
  background: white;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.page-card--flex {
  display: flex;
  flex-direction: column;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  padding: 14px 20px;
  border-bottom: 1px solid #f1f5f9;
}

.section-header--nowrap {
  flex-wrap: nowrap;
  overflow-x: auto;
  scrollbar-width: none;
}
.section-header--nowrap::-webkit-scrollbar {
  display: none;
}

.section-header__left {
  flex: 1;
  min-width: 0;
}

.kline-wrapper {
  flex: 1;
  min-height: 200px;
  max-height: 500px;
}
</style>