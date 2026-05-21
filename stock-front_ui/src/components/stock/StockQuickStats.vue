<script setup lang="ts">
import { ElRow, ElCol } from 'element-plus'
import type { StockDaily } from '@/types/stock'

defineProps<{
  latestDaily: StockDaily | null
}>()

function formatVol(v: number) {
  if (v == null || v === 0) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + ' 亿'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + ' 万'
  return String(v)
}
</script>

<template>
  <el-row :gutter="12" class="quick-stats">
    <el-col :span="6">
      <div class="quick-stat">
        <div class="quick-stat__label">今开</div>
        <div class="quick-stat__value">{{ latestDaily?.open?.toFixed(2) ?? '-' }}</div>
      </div>
    </el-col>
    <el-col :span="6">
      <div class="quick-stat">
        <div class="quick-stat__label">最高</div>
        <div class="quick-stat__value text-rise">{{ latestDaily?.high?.toFixed(2) ?? '-' }}</div>
      </div>
    </el-col>
    <el-col :span="6">
      <div class="quick-stat">
        <div class="quick-stat__label">最低</div>
        <div class="quick-stat__value text-fall">{{ latestDaily?.low?.toFixed(2) ?? '-' }}</div>
      </div>
    </el-col>
    <el-col :span="6">
      <div class="quick-stat">
        <div class="quick-stat__label">成交量</div>
        <div class="quick-stat__value">{{ formatVol(latestDaily?.volume ?? 0) }}</div>
      </div>
    </el-col>
  </el-row>
</template>

<style scoped>
.quick-stats {
  margin-bottom: 4px;
}

.quick-stat {
  background: white;
  border-radius: var(--radius-md);
  padding: 14px 16px;
  box-shadow: var(--shadow-sm);
  border: 1px solid rgba(0, 0, 0, 0.04);
  text-align: center;
}

.quick-stat__label {
  font-size: 11px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.quick-stat__value {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}
</style>