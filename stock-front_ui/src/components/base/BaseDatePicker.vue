<script setup lang="ts">
/**
 * BaseDatePicker — 日期选择器封装
 * 统一格式 YYYY-MM-DD，支持日期和日期范围
 */

withDefaults(defineProps<{
    modelValue?: string | [string, string]
    placeholder?: string
    type?: 'date' | 'daterange'
    disabled?: boolean
    clearable?: boolean
    startPlaceholder?: string
    endPlaceholder?: string
  }>(),
  {
    type: 'date',
    disabled: false,
    clearable: true,
  }
)

const emit = defineEmits<{
  'update:modelValue': [val: string | [string, string] | undefined]
}>()

function onUpdate(val: string | [string, string] | null) {
  emit('update:modelValue', val ?? undefined)
}
</script>

<template>
  <el-date-picker
    :model-value="modelValue"
    :type="type === 'daterange' ? 'daterange' : 'date'"
    :placeholder="type === 'daterange' ? undefined : (placeholder ?? '请选择日期')"
    :start-placeholder="type === 'daterange' ? (startPlaceholder ?? '开始日期') : undefined"
    :end-placeholder="type === 'daterange' ? (endPlaceholder ?? '结束日期') : undefined"
    :disabled="disabled"
    :clearable="clearable"
    value-format="YYYY-MM-DD"
    style="width: 100%"
    @update:model-value="onUpdate"
  />
</template>
