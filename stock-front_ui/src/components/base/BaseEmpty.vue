<script setup lang="ts">
/**
 * BaseEmpty — 通用空状态组件
 * 显示空状态插画 + 文案
 */
import { ElEmpty } from 'element-plus'

withDefaults(
  defineProps<{
    description?: string
    imageSize?: number
  }>(),
  {
    description: '暂无数据',
    imageSize: 80,
  }
)
</script>

<template>
  <el-empty :description="description" :image-size="imageSize" />
</template>
