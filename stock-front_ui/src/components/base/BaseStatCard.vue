<script setup lang="ts">
/**
 * BaseStatCard — 统计卡片
 * 封装 el-card + el-statistic，支持前缀/后缀、自定义颜色
 */
import { ElCard } from 'element-plus'

withDefaults(
  defineProps<{
    title: string
    value?: string | number
    prefix?: string
    suffix?: string
    prefixColor?: string
    valueColor?: string
    loading?: boolean
  }>(),
  {
    prefixColor: '',
    valueColor: '',
    loading: false,
  }
)
</script>

<template>
  <el-card shadow="hover" :body-style="{ padding: '20px 24px' }">
    <el-skeleton v-if="loading" :rows="1" animated />
    <template v-else>
      <div class="stat-label">{{ title }}</div>
      <div class="stat-value-wrap">
        <span v-if="prefix" class="stat-prefix" :style="{ color: prefixColor }">{{ prefix }}</span>
        <span class="stat-value" :style="{ color: valueColor }">{{ value ?? '-' }}</span>
        <span v-if="suffix" class="stat-suffix">{{ suffix }}</span>
      </div>
    </template>
  </el-card>
</template>

<style scoped>
.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value-wrap {
  display: flex;
  align-items: baseline;
  gap: 2px;
  font-size: 24px;
  font-weight: 600;
}

.stat-prefix,
.stat-suffix {
  font-size: 14px;
  color: #606266;
}
</style>
