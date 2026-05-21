<script setup lang="ts">
/**
 * FilterPanel.vue — 选股筛选条件面板
 * 支持：交易日选择、行业选择、排除ST、换手率、ROE、趋势评分等
 * 用法：<FilterPanel v-model:filters="filters" v-model:trade-date="selectedDate" ... />
 */
import { ref, onMounted, watch } from 'vue'
import { ElForm, ElFormItem, ElSelect, ElOption, ElInput, ElCheckbox, ElButton } from 'element-plus'
import type { SelectionFilters } from '@/types/selection'
import { selectionApi } from '@/api/selection'

const props = defineProps<{
  filters: SelectionFilters
  tradeDate?: string
  tradeDates?: string[]
  industries?: string[]
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:filters': [filters: SelectionFilters]
  'update:tradeDate': [date: string]
  search: []
}>()

// 交易日下拉（如果父组件没传，从API拉）
const internalDates = ref<string[]>(props.tradeDates ?? [])

onMounted(async () => {
  if (!props.tradeDates?.length) {
    try {
      const datesRes = await selectionApi.getDates({ limit: 100 })
      internalDates.value = datesRes.data ?? []
    } catch {
      // ignore
    }
  }
})

// 排除ST本地状态（从父组件 filters 同步）
const excludeSt = ref(false)

watch(
  () => props.filters?.is_st,
  (val) => {
    // is_st=false 表示排除ST → excludeSt=true
    excludeSt.value = val === false
  },
  { immediate: true }
)

// 同步 emit
function updateFilter(key: keyof SelectionFilters, value: any) {
  emit('update:filters', { ...props.filters, [key]: value })
}

/** 触发搜索 */
function handleSearch() {
  const filters: SelectionFilters = {
    ...props.filters,
    is_st: excludeSt.value ? false : undefined,
  }
  emit('update:filters', filters)
  emit('search')
}

/** 重置 */
function handleReset() {
  excludeSt.value = false
  emit('update:filters', {})
  emit('search')
}
</script>

<template>
  <div class="filter-panel">
    <el-form @submit.prevent="handleSearch">
      <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center;">
        <el-form-item label="交易日">
          <el-select
            :model-value="tradeDate"
            placeholder="选择交易日"
            style="width: 140px"
            clearable
            @update:model-value="emit('update:tradeDate', $event ?? '')"
          >
            <el-option v-for="d in (tradeDates ?? internalDates)" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>

        <el-form-item label="行业">
          <el-select
            :model-value="filters.industry_l1"
            placeholder="全部"
            style="width: 140px"
            clearable
            @update:model-value="updateFilter('industry_l1', $event)"
          >
            <el-option v-for="ind in (industries ?? [])" :key="ind" :label="ind" :value="ind" />
          </el-select>
        </el-form-item>

        <el-form-item label="排除ST">
          <el-checkbox v-model="excludeSt" />
        </el-form-item>

        <el-form-item label="ROE≥">
          <el-input
            :model-value="filters.roe_min"
            type="number"
            placeholder="0"
            style="width: 80px"
            @update:model-value="updateFilter('roe_min', $event != null ? Number($event) : undefined)"
          />
        </el-form-item>

        <el-form-item label="换手率≥">
          <el-input
            :model-value="filters.turnover_rate_min"
            type="number"
            placeholder="0"
            style="width: 80px"
            @update:model-value="updateFilter('turnover_rate_min', $event != null ? Number($event) : undefined)"
          />
        </el-form-item>

        <el-form-item label="趋势评分≥">
          <el-input
            :model-value="filters.trend_score_min"
            type="number"
            placeholder="0"
            style="width: 80px"
            @update:model-value="updateFilter('trend_score_min', $event != null ? Number($event) : undefined)"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click.stop="handleSearch">查询</el-button>
          <el-button @click.stop="handleReset">重置</el-button>
        </el-form-item>
      </div>
    </el-form>
  </div>
</template>

<style scoped>
.filter-panel {
  padding: 4px 0;
}
</style>
