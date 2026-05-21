<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { stockApi } from '@/api/stock'
import { strategyApi, type StrategyAnalysisResult } from '@/api/strategy'
import { useRouter } from 'vue-router'

const router = useRouter()

const searchQuery = ref('')
const searchResults = ref<{ symbol: string; name: string; exchange: string }[]>([])
const selectedStock = ref<{ symbol: string; name: string } | null>(null)
const loading = ref(false)

interface AnalyzeData {
  symbol: string
  name: string
  exchange: string
  close: number | null
  change_pct: number | null
  turnover_rate: number | null
  ma5: number | null
  ma10: number | null
  ma20: number | null
  volume_ratio: number | null
  trend_score: number | null
  trade_date: string
  results: StrategyAnalysisResult[]
}

const analyzeData = ref<AnalyzeData | null>(null)
const analyzing = ref(false)

async function onSearch(q: string) {
  if (!q.trim()) {
    searchResults.value = []
    return
  }
  try {
    const res = await stockApi.search(q, 5)
    searchResults.value = res.data ?? []
  } catch {
    searchResults.value = []
  }
}

function selectStock(stock: { symbol: string; name: string; exchange: string }) {
  selectedStock.value = { symbol: stock.symbol, name: stock.name }
  searchQuery.value = stock.name
  searchResults.value = []
  runAnalysis()
}

async function runAnalysis() {
  if (!selectedStock.value) return
  analyzing.value = true
  analyzeData.value = null
  try {
    const res = await strategyApi.analyzeStock(selectedStock.value.symbol)
    analyzeData.value = res.data as AnalyzeData
  } catch (e: unknown) {
    ElMessage.error((e as { message?: string })?.message ?? '分析失败，请重试')
  } finally {
    analyzing.value = false
  }
}

function goToStockDetail(symbol: string) {
  router.push(`/stocks/${symbol}`)
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-header__title">问股</h1>
        <p class="page-header__sub">输入股票代码或名称，系统用9种策略分析其走势特征与买卖信号</p>
      </div>
    </div>

    <!-- 搜索区 -->
    <div class="search-card">
      <div class="search-box">
        <el-input
          v-model="searchQuery"
          placeholder="输入股票代码或名称，如 贵州茅台 / 600519"
          size="large"
          clearable
          @input="onSearch($event as string)"
          @clear="selectedStock = null; analyzeData = null"
        />
        <el-button
          v-if="selectedStock"
          type="primary"
          size="large"
          :loading="analyzing"
          @click="runAnalysis"
        >
          重新分析
        </el-button>
      </div>
      <!-- 搜索下拉 -->
      <div v-if="searchResults.length > 0" class="search-dropdown">
        <div
          v-for="s in searchResults"
          :key="s.symbol"
          class="search-item"
          @click="selectStock(s)"
        >
          <span class="search-item__symbol">{{ s.symbol }}</span>
          <span class="search-item__name">{{ s.name }}</span>
          <span class="search-item__exchange">{{ s.exchange === 'SH' ? '上交所' : '深交所' }}</span>
        </div>
      </div>
    </div>

    <!-- 分析结果 -->
    <div v-if="analyzeData" class="results">
      <!-- 股票概览 -->
      <div class="stock-overview">
        <div class="stock-overview__left">
          <span class="stock-overview__name">{{ analyzeData.name }}</span>
          <span class="stock-overview__symbol">{{ analyzeData.symbol }}</span>
          <span class="stock-overview__exchange">{{ analyzeData.exchange === 'SH' ? '上交所' : '深交所' }}</span>
        </div>
        <div class="stock-overview__metrics">
          <div class="metric">
            <span class="metric__label">收盘价</span>
            <span class="metric__value">{{ analyzeData.close?.toFixed(2) ?? '-' }}</span>
          </div>
          <div class="metric">
            <span class="metric__label">涨跌幅</span>
            <span
              class="metric__value"
              :class="{
                'text-rise': analyzeData.change_pct && analyzeData.change_pct > 0,
                'text-fall': analyzeData.change_pct && analyzeData.change_pct < 0,
              }"
            >
              {{ analyzeData.change_pct != null ? (analyzeData.change_pct > 0 ? '+' : '') + analyzeData.change_pct.toFixed(2) + '%' : '-' }}
            </span>
          </div>
          <div class="metric">
            <span class="metric__label">换手率</span>
            <span class="metric__value">{{ analyzeData.turnover_rate != null ? analyzeData.turnover_rate.toFixed(2) + '%' : '-' }}</span>
          </div>
          <div class="metric">
            <span class="metric__label">MA20</span>
            <span class="metric__value">{{ analyzeData.ma20?.toFixed(2) ?? '-' }}</span>
          </div>
          <div class="metric">
            <span class="metric__label">趋势评分</span>
            <span class="metric__value">{{ analyzeData.trend_score?.toFixed(1) ?? '-' }}</span>
          </div>
        </div>
      </div>

      <!-- 策略结果 -->
      <div class="strategy-list">
        <div
          v-for="r in analyzeData.results"
          :key="r.strategy_id"
          class="strategy-item"
          :class="{ 'strategy-item--triggered': r.triggered }"
        >
          <div class="strategy-item__header">
            <div class="strategy-item__title">
              <span class="strategy-item__name">{{ r.strategy_name }}</span>
              <el-tag size="small" :type="r.triggered ? 'success' : 'info'" effect="plain">
                {{ r.triggered ? '✅ 触发' : '❌ 未触发' }}
              </el-tag>
              <el-tag v-if="r.triggered" size="small" type="warning" effect="plain">
                评分 {{ r.score }}
              </el-tag>
            </div>
          </div>

          <div v-if="r.triggered" class="strategy-item__body">
            <div class="strategy-item__reason">{{ r.match_reason }}</div>
            <div class="strategy-item__signals">
              <el-tag
                v-for="sig in r.signals"
                :key="sig.name"
                size="small"
                type="success"
                effect="plain"
                style="margin: 2px 4px;"
              >
                {{ sig.name }}: {{ sig.value }}
              </el-tag>
            </div>
          </div>

          <div v-else class="strategy-item__body">
            <span class="strategy-item__reason">{{ r.match_reason }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!selectedStock" class="empty-state">
      <div class="empty-state__icon">🔍</div>
      <p class="empty-state__text">输入股票代码或名称，开始分析</p>
      <div class="strategy-tags">
        <el-tag size="small" effect="plain">底部放量</el-tag>
        <el-tag size="small" effect="plain">箱体震荡</el-tag>
        <el-tag size="small" effect="plain">多头趋势</el-tag>
        <el-tag size="small" effect="plain">缠论</el-tag>
        <el-tag size="small" effect="plain">均线金叉</el-tag>
        <el-tag size="small" effect="plain">一阳夹三阴</el-tag>
        <el-tag size="small" effect="plain">缩量回踩</el-tag>
        <el-tag size="small" effect="plain">放量突破</el-tag>
        <el-tag size="small" effect="plain">波浪理论</el-tag>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  padding: 24px;
  max-width: 1100px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header__title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 4px;
}

.page-header__sub {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0;
}

/* 搜索卡片 */
.search-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  position: relative;
}

.search-box {
  display: flex;
  gap: 12px;
}

.search-box .el-input {
  flex: 1;
}

.search-dropdown {
  position: absolute;
  top: calc(100% - 8px);
  left: 20px;
  right: 20px;
  background: white;
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
  overflow: hidden;
}

.search-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.15s;
}

.search-item:hover {
  background: #f8fafc;
}

.search-item__symbol {
  font-weight: 600;
  color: var(--el-color-primary);
  font-size: 13px;
}

.search-item__name {
  flex: 1;
  font-size: 14px;
  color: var(--color-text-primary);
}

.search-item__exchange {
  font-size: 12px;
  color: var(--color-text-muted);
}

/* 股票概览 */
.stock-overview {
  background: white;
  border-radius: 12px;
  padding: 18px 20px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.stock-overview__left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stock-overview__name {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.stock-overview__symbol {
  font-size: 13px;
  color: var(--color-text-muted);
}

.stock-overview__exchange {
  font-size: 12px;
  color: var(--color-text-muted);
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
}

.stock-overview__metrics {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.metric {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.metric__label {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-bottom: 2px;
}

.metric__value {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.text-rise { color: #ef4444 !important; }
.text-fall { color: #22c55e !important; }

/* 策略列表 */
.strategy-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.strategy-item {
  background: white;
  border-radius: 10px;
  padding: 14px 18px;
  border: 2px solid #f1f5f9;
}

.strategy-item--triggered {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.strategy-item__header {
  margin-bottom: 8px;
}

.strategy-item__title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strategy-item__name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.strategy-item__body {
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
}

.strategy-item__reason {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.strategy-item__signals {
  display: flex;
  flex-wrap: wrap;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px 0;
}

.empty-state__icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state__text {
  font-size: 16px;
  color: var(--color-text-muted);
  margin-bottom: 20px;
}

.strategy-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
</style>
