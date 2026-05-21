<script setup lang="ts">
import { computed } from 'vue'
import { ElCard, ElIcon, ElProgress, ElAlert } from 'element-plus'
import { DataAnalysis, List } from '@element-plus/icons-vue'
import type { CoverageSummary } from '@/types/dashboard'

const props = defineProps<{
  coverage: CoverageSummary | null
  loading: boolean
}>()

const backfillProgress = computed(() => {
  if (!props.coverage || !props.coverage.total_symbols) {
    return { daily: 0, finance: 0 }
  }
  const t = props.coverage.total_symbols
  return {
    daily: Math.round((props.coverage.daily_fully_covered_symbols / t) * 100),
    finance: Math.round((props.coverage.financial_fully_covered_symbols / t) * 100),
  }
})

const stocksNeedBackfill = computed(() => {
  if (!props.coverage) return 0
  return props.coverage.total_symbols - props.coverage.daily_fully_covered_symbols
})
</script>

<template>
  <el-card shadow="hover" class="mid-card" :body-style="{ padding: '20px 24px' }">
    <template #header>
      <div class="card-header">
        <span class="card-title">
          <el-icon><DataAnalysis /></el-icon>
          数据覆盖
        </span>
      </div>
    </template>

    <div v-if="loading" class="coverage-loading">
      <el-icon class="is-loading"><DataAnalysis /></el-icon>
    </div>

    <div v-else-if="coverage" class="coverage-content">
      <div class="coverage-summary">
        <span class="coverage-summary__label">股票总数</span>
        <span class="coverage-summary__value">{{ coverage.total_symbols }}</span>
        <span class="coverage-summary__unit">只</span>
      </div>

      <div class="coverage-item">
        <div class="coverage-item__header">
          <span class="coverage-item__label">
            <el-icon><List /></el-icon>
            日线完整
          </span>
          <span class="coverage-item__value">
            {{ coverage.daily_fully_covered_symbols }} / {{ coverage.total_symbols }} 只
          </span>
        </div>
        <el-progress
          :percentage="backfillProgress.daily"
          :stroke-width="8"
          :color="backfillProgress.daily >= 90 ? '#67C23A' : '#E6A23C'"
          :show-text="true"
        />
      </div>

      <div class="coverage-item">
        <div class="coverage-item__header">
          <span class="coverage-item__label">
            <el-icon><DataAnalysis /></el-icon>
            财务完整
          </span>
          <span class="coverage-item__value">
            {{ coverage.financial_fully_covered_symbols }} / {{ coverage.total_symbols }} 只
          </span>
        </div>
        <el-progress
          :percentage="backfillProgress.finance"
          :stroke-width="8"
          :color="backfillProgress.finance >= 90 ? '#67C23A' : '#E6A23C'"
          :show-text="true"
        />
      </div>

      <el-alert
        v-if="stocksNeedBackfill > 0"
        :title="`还有 ${stocksNeedBackfill} 只股票数据不完整`"
        type="warning"
        :closable="false"
        show-icon
        class="coverage-alert"
      />
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

.coverage-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 120px;
  color: var(--color-text-muted);
}

.coverage-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.coverage-summary {
  display: flex;
  align-items: baseline;
  gap: 4px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.coverage-summary__label {
  font-size: 13px;
  color: var(--color-text-muted);
  margin-right: 6px;
}

.coverage-summary__value {
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.coverage-summary__unit {
  font-size: 13px;
  color: var(--color-text-muted);
}

.coverage-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.coverage-item__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.coverage-item__label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.coverage-item__value {
  font-size: 13px;
  color: var(--color-text-muted);
}

.coverage-alert {
  margin-top: 4px;
}
</style>