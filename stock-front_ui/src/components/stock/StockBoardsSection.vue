<script setup lang="ts">
import { ElIcon, ElTag } from 'element-plus'
import { Link } from '@element-plus/icons-vue'
import type { StockBoard } from '@/types/stock'

defineProps<{
  boards: StockBoard[]
}>()
</script>

<template>
  <div v-if="boards.length > 0" class="page-card" style="margin-bottom: 16px">
    <div class="section-header">
      <el-icon><Link /></el-icon> 所属板块
    </div>
    <div class="board-tags">
      <el-tag v-for="b in boards" :key="b.board_code" class="board-tag" effect="plain" round>
        {{ b.board_name }}
      </el-tag>
    </div>
  </div>
</template>

<style scoped>
.page-card {
  background: white;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  padding: 14px 20px;
  border-bottom: 1px solid #f1f5f9;
}

.board-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 14px 20px;
}

.board-tag {
  cursor: pointer;
}
</style>