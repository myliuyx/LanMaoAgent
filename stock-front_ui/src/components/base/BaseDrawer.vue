<script setup lang="ts">
/**
 * BaseDrawer — 抽屉封装
 * 统一尺寸配置，自动 emit close
 */
import { ElDrawer } from 'element-plus'

withDefaults(defineProps<{
    modelValue: boolean
    title?: string
    size?: 'small' | 'medium' | 'large'
    destroyOnClose?: boolean
  }>(),
  {
    title: '',
    size: 'medium',
    destroyOnClose: true,
  }
)

const emit = defineEmits<{
  'update:modelValue': [val: boolean]
  close: []
}>()

const sizeMap = { small: '320px', medium: '480px', large: '720px' }

function onClose() {
  emit('update:modelValue', false)
  emit('close')
}
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    :title="title"
    :size="sizeMap[size]"
    :destroy-on-close="destroyOnClose"
    :with-header="!!title"
    @close="onClose"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <slot />
    <template #footer>
      <slot name="footer" />
    </template>
  </el-drawer>
</template>
