<script setup lang="ts">
import { ElCard, ElTable, ElTableColumn, ElTag, ElIcon } from 'element-plus'
import { TrendCharts } from '@element-plus/icons-vue'
import type { WatchlistAnalysisResult } from '@/types/dashboard'

defineProps<{
  watchlistAnalysis: WatchlistAnalysisResult | null
  watchlistLoading: boolean
}>()
</script>

<template>
  <el-card shadow="hover" class="mid-card" :body-style="{ padding: '0' }">
    <template #header>
      <div class="card-header">
        <span class="card-title">
          <el-icon><TrendCharts /></el-icon>
          自选股分析
        </span>
        <el-tag v-if="watchlistAnalysis" size="small" type="info">
          {{ watchlistAnalysis.summary.total }}只
        </el-tag>
      </div>
    </template>

    <!-- 汇总统计 -->
    <div v-if="watchlistAnalysis" class="analysis-summary">
      <div class="analysis-summary__item">
        <span class="analysis-summary__label">今日涨跌</span>
        <span class="analysis-summary__value up">{{ watchlistAnalysis.summary.up_count }}</span>
        <span class="analysis-summary__sep"> / </span>
        <span class="analysis-summary__value down">{{ watchlistAnalysis.summary.down_count }}</span>
      </div>
      <div class="analysis-summary__item">
        <span class="analysis-summary__label">胜率</span>
        <span class="analysis-summary__value">{{ watchlistAnalysis.summary.up_rate }}%</span>
      </div>
      <div class="analysis-summary__item">
        <span class="analysis-summary__label">多头排列</span>
        <span class="analysis-summary__value highlight">{{ watchlistAnalysis.summary.bullish_count }}</span>
      </div>
      <div class="analysis-summary__item">
        <span class="analysis-summary__label">量能异动</span>
        <span class="analysis-summary__value warning">{{ watchlistAnalysis.summary.volume_alert_count }}</span>
      </div>
    </div>

    <!-- 信号表格 -->
    <el-table
      v-if="watchlistAnalysis && watchlistAnalysis.stocks.length > 0"
      :data="watchlistAnalysis.stocks"
      v-loading="watchlistLoading"
      stripe
      size="small"
      max-height="415"
      style="width: 100%"
    >
      <el-table-column prop="name" label="股票" width="110" align="center">
        <template #default="{ row }">
          <router-link :to="`/stocks/${row.symbol}`" class="stock-link">
            {{ row.name }}
          </router-link>
          <div class="stock-code">{{ row.symbol }}</div>
        </template>
      </el-table-column>
      <el-table-column label="最新价" width="80" align="right">
        <template #default="{ row }">
          <span :class="row.change_pct > 0 ? 'price-up' : row.change_pct < 0 ? 'price-down' : ''">
            {{ row.close ? row.close.toFixed(2) : '-' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="信号提示" min-width="160" align="center">
        <template #default="{ row }">
          <div class="signal-tags">
            <el-tag
              v-for="sig in row.signals.slice(0, 3)"
              :key="sig"
              size="small"
              :type="sig.includes('多头') ? 'success' : sig.includes('空头') ? 'danger' : sig.includes('高位') ? 'warning' : sig.includes('低位') ? 'warning' : sig.includes('异动') ? 'danger' : 'info'"
            >
              {{ sig }}
            </el-tag>
            <span v-if="row.signals.length === 0" class="no-signal">暂无信号</span>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div v-else-if="!watchlistLoading" class="empty-tip">
      暂无自选股数据
    </div>
  </el-card>
</template>

<style scoped>
.mid-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.analysis-summary {
  display: flex;
  gap: 16px;
  padding: 12px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
}

.analysis-summary__item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}

.analysis-summary__label {
  color: var(--color-text-muted);
}

.analysis-summary__value {
  font-weight: 600;
  color: var(--color-text-primary);
}

.analysis-summary__value.up { color: var(--color-rise); }
.analysis-summary__value.down { color: var(--color-fall); }
.analysis-summary__value.highlight { color: var(--color-rise); }
.analysis-summary__value.warning { color: var(--color-fall); }

.analysis-summary__sep {
  color: #d1d5db;
}

.stock-link {
  color: var(--color-primary, #409eff);
  text-decoration: none;
  font-size: 13px;
}

.stock-link:hover {
  text-decoration: underline;
}

.stock-code {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 1px;
}

.price-up { color: var(--color-rise); font-weight: 600; }
.price-down { color: var(--color-fall); font-weight: 600; }

.signal-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  justify-content: center;
}

.no-signal {
  font-size: 12px;
  color: var(--color-text-muted);
}

.empty-tip {
  padding: 32px 0;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 13px;
}
</style>