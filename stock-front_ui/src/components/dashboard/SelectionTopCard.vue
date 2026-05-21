<script setup lang="ts">
import { ElCard, ElTable, ElTableColumn, ElTag, ElIcon } from 'element-plus'
import { Top } from '@element-plus/icons-vue'
import type { SelectionTopItem } from '@/types/selection'

defineProps<{
  selectionTop: SelectionTopItem[]
  selectionTopLoading: boolean
}>()
</script>

<template>
  <el-card shadow="hover" class="mid-card" :body-style="{ padding: '0' }">
    <template #header>
      <div class="card-header">
        <span class="card-title">
          <el-icon><Top /></el-icon>
          选股Top榜
        </span>
        <el-tag size="small" type="primary">近5日</el-tag>
      </div>
    </template>
    <el-table
      :data="selectionTop"
      v-loading="selectionTopLoading"
      stripe
      size="small"
      max-height="475"
      style="width: 100%"
    >
      <el-table-column label="#" width="40" align="center">
        <template #default="{ $index }">
          <span class="rank-num" :class="{ 'rank-top': $index < 3 }">{{ $index + 1 }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="股票" min-width="70">
        <template #default="{ row }">
          <router-link :to="`/stocks/${row.symbol}`" class="stock-link">
            {{ row.name }}
          </router-link>
          <div class="stock-code">{{ row.symbol }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="industry_l1" label="行业" width="200" show-overflow-tooltip />
      <el-table-column label="入选次数" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small" type="primary">{{ row.selection_count }}次</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="综合评分" width="100" align="center">
        <template #default="{ row }">
          <span class="score-val">{{ row.avg_trend_score ?? '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="信号" width="120" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.is_new_high_60d" size="small" type="warning">60日新高</el-tag>
          <el-tag v-else-if="row.is_break_ma20" size="small" type="success">突破MA20</el-tag>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="!selectionTopLoading && selectionTop.length === 0" class="empty-tip">
      暂无选股数据
    </div>
  </el-card>
</template>

<style scoped>
.mid-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.rank-num {
  font-size: 13px;
  color: var(--color-text-muted);
}

.rank-num.rank-top {
  color: var(--color-primary, #409eff);
  font-weight: 700;
}

.stock-link {
  color: var(--color-primary, #409eff);
  text-decoration: none;
  font-size: 13px;
}

.stock-link:hover {
  text-decoration: underline;
}

.stock-code {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 1px;
}

.score-val {
  font-weight: 600;
  color: var(--color-text-primary);
}

.text-muted {
  color: var(--color-text-muted);
}

.empty-tip {
  padding: 32px 0;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 13px;
}
</style>