<script setup lang="ts">
/**
 * ResultTable — 选股结果表格
 * 支持列定义、排序、行点击
 */
import { ElTable, ElTableColumn, ElTag } from 'element-plus'
import { formatPercent } from '@/utils/format'
import type { SelectionItem } from '@/types/selection'

const props = withDefaults(
  defineProps<{
    data: SelectionItem[]
    loading?: boolean
    emptyText?: string
    height?: string | number
  }>(),
  {
    loading: false,
    emptyText: '暂无符合条件的数据',
    height: undefined,
  }
)


const emit = defineEmits<{
  'row-click': [row: SelectionItem]
  'sort-change': [payload: { prop: string; order: string }]
}>()

function formatChangePct(val: number | null | undefined): string {
  if (val == null) return '-'
  return (val >= 0 ? '+' : '') + val.toFixed(2) + '%'
}

function changeClass(val: number | null | undefined): string {
  if (val == null) return ''
  return val > 0 ? 'text-rise' : val < 0 ? 'text-fall' : ''
}

function formatTurnoverRate(val: number | null | undefined): string {
  if (val == null) return '-'
  return formatPercent(val)
}

function formatRoe(val: number | null | undefined): string {
  if (val == null) return '-'
  return formatPercent(val)
}

function formatTrendScore(val: number | null | undefined): string {
  if (val == null) return '-'
  return val.toFixed(1)
}
</script>

<template>
  <el-table
    :data="props.data"
    stripe
    border
    style="width: 100%; table-layout: fixed"
    :loading="props.loading"
    :height="props.height"
    row-class-name="clickable-row"
    @row-click="(row: SelectionItem) => emit('row-click', row)"
    @sort-change="(payload: any) => emit('sort-change', payload)"
  >
    <el-table-column prop="symbol" label="代码" width="110" sortable="custom" />
    <el-table-column prop="name" label="名称" min-width="120" />
    <el-table-column prop="exchange" label="交易所" width="70" />
    <el-table-column prop="industry_l1" label="行业" min-width="120" :show-overflow-tooltip="true" />
    <el-table-column prop="close" label="收盘价" width="100" align="right" sortable="custom">
      <template #default="{ row }">
        {{ row.close != null ? row.close.toFixed(2) : '-' }}
      </template>
    </el-table-column>
    <el-table-column prop="change_pct" label="涨跌幅" width="100" align="right" sortable="custom">
      <template #default="{ row }">
        <span :class="changeClass(row.change_pct)">{{ formatChangePct(row.change_pct) }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="turnover_rate" label="换手率" width="90" align="right" sortable="custom">
      <template #default="{ row }">
        {{ formatTurnoverRate(row.turnover_rate) }}
      </template>
    </el-table-column>
    <el-table-column prop="roe" label="ROE" width="90" align="right" sortable="custom">
      <template #default="{ row }">
        {{ formatRoe(row.roe) }}
      </template>
    </el-table-column>
    <el-table-column prop="trend_score" label="趋势评分" width="100" align="right" sortable="custom">
      <template #default="{ row }">
        {{ formatTrendScore(row.trend_score) }}
      </template>
    </el-table-column>
    <el-table-column prop="is_new_high_60d" label="60日新高" width="100">
      <template #default="{ row }">
        <el-tag v-if="row.is_new_high_60d" type="success" size="small">是</el-tag>
        <span v-else>-</span>
      </template>
    </el-table-column>
    <el-table-column prop="is_break_ma20" label="突破MA20" width="100">
      <template #default="{ row }">
        <el-tag v-if="row.is_break_ma20" type="warning" size="small">是</el-tag>
        <span v-else>-</span>
      </template>
    </el-table-column>
    <el-table-column prop="is_st" label="ST" width="70">
      <template #default="{ row }">
        <el-tag v-if="row.is_st" type="danger" size="small">ST</el-tag>
      </template>
    </el-table-column>
    <template #empty>
      <span style="color: #909399; font-size: 14px">{{ props.emptyText }}</span>
    </template>
  </el-table>
</template>

<style scoped>
:deep(.clickable-row) {
  cursor: pointer;
}
</style>
