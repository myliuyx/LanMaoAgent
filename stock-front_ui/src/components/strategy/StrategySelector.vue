<script setup lang="ts">
/**
 * StrategySelector.vue — 问股策略选择器
 * 支持：选择9种交易策略、查看策略描述、切换策略模式
 */
import { ref, onMounted, computed } from 'vue'
import { ElSelect, ElOption, ElTag, ElTooltip } from 'element-plus'
import { strategyApi } from '@/api/strategy'
import type { Strategy } from '@/types/strategy'

const props = defineProps<{
  modelValue?: string
  tradeDate?: string
  tradeDates?: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [strategyId: string]
  change: [strategyId: string]
}>()

const strategies = ref<Strategy[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const res = await strategyApi.listStrategies()
    strategies.value = res.data ?? []
  } finally {
    loading.value = false
  }
})

const selectedStrategy = computed({
  get: () => props.modelValue ?? '',
  set: (val) => {
    emit('update:modelValue', val)
    if (val) emit('change', val)
  },
})

// 按 priority 排序
const sortedStrategies = computed(() =>
  [...strategies.value].sort((a, b) => a.priority - b.priority)
)

// 优先级对应的 Tag 类型
function getPriorityType(priority: number): 'success' | 'warning' | 'info' {
  if (priority <= 20) return 'success'
  if (priority <= 50) return 'warning'
  return 'info'
}

// 优先级标签
function getPriorityLabel(priority: number): string {
  if (priority <= 20) return '高优'
  if (priority <= 50) return '中优'
  return '常规'
}
</script>

<template>
  <div class="strategy-selector">
    <el-select
      v-model="selectedStrategy"
      placeholder="选择策略（可选9种）"
      style="width: 260px"
      clearable
      :loading="loading"
      @clear="emit('update:modelValue', '')"
    >
      <el-option
        v-for="s in sortedStrategies"
        :key="s.id"
        :label="s.name"
        :value="s.id"
      >
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-weight: 600;">{{ s.name }}</span>
          <el-tag size="small" :type="getPriorityType(s.priority)" effect="plain">
            {{ getPriorityLabel(s.priority) }} #{{ s.priority }}
          </el-tag>
        </div>
      </el-option>
    </el-select>

    <!-- 选中策略后显示描述 -->
    <div v-if="selectedStrategy" class="strategy-desc">
      <template v-for="s in sortedStrategies" :key="s.id">
        <div v-if="s.id === selectedStrategy" class="strategy-desc__inner">
          <span class="strategy-desc__name">{{ s.name }}</span>
          <span class="strategy-desc__text">{{ s.description }}</span>
          <div class="strategy-desc__signals">
            <el-tooltip
              v-for="sig in s.signals"
              :key="sig"
              :content="sig"
              placement="top"
            >
              <el-tag size="small" effect="plain" style="margin: 0 2px;">
                {{ sig }}
              </el-tag>
            </el-tooltip>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.strategy-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.strategy-desc {
  font-size: 13px;
}

.strategy-desc__inner {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.strategy-desc__name {
  font-weight: 600;
  color: var(--el-color-primary);
}

.strategy-desc__text {
  color: var(--el-color-info);
}

.strategy-desc__signals {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  margin-left: 4px;
}
</style>