<script setup lang="ts">
/**
 * BaseTag — 状态标签
 * 传入 status 自动映射 label + type，支持自定义映射表
 */
import { computed } from 'vue'
import { ElTag } from 'element-plus'

const props = withDefaults(
  defineProps<{
    /** 状态值 */
    status: string
    /** 状态映射表，默认值 */
    map?: Record<string, { label: string; type?: string }>
    /** 默认显示的文字（map 中找不到时） */
    defaultLabel?: string
    size?: 'large' | 'default' | 'small'
  }>(),
  {
    defaultLabel: '',
    size: 'small',
  }
)

const DEFAULT_MAP: Record<string, { label: string; type: string }> = {
  // 通用
  true: { label: '是', type: 'success' },
  false: { label: '否', type: 'info' },
  // 任务状态
  PENDING: { label: '排队中', type: 'info' },
  RUNNING: { label: '运行中', type: 'warning' },
  SUCCESS: { label: '成功', type: 'success' },
  FAILED: { label: '失败', type: 'danger' },
  CANCELLED: { label: '已取消', type: 'info' },
}

const resolved = computed(() => {
  const m = { ...DEFAULT_MAP, ...(props.map ?? {}) }
  return m[props.status] ?? { label: props.defaultLabel || props.status, type: 'info' }
})
</script>

<template>
  <el-tag :type="(resolved.type as any) ?? 'info'" :size="size">
    {{ resolved.label }}
  </el-tag>
</template>
