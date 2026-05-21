<script setup lang="ts">
import { ElCard, ElTable, ElTableColumn, ElTag, ElIcon } from 'element-plus'
import { Timer, CircleCheck, CircleClose, Loading } from '@element-plus/icons-vue'
import type { JobItem, JobStatus } from '@/types/job'
import { formatDuration } from '@/utils/format'

defineProps<{
  jobs: JobItem[]
  loading: boolean
}>()

const statusConfig: Record<string, { type: 'success' | 'danger' | 'primary' | 'info' | 'warning'; label: string; icon: any }> = {
  SUCCESS:  { type: 'success', label: '成功', icon: CircleCheck },
  FAILED:   { type: 'danger',  label: '失败', icon: CircleClose },
  RUNNING:  { type: 'primary', label: '运行中', icon: Loading },
  PENDING:  { type: 'info',    label: '等待中', icon: Timer },
  CANCELLED:{ type: 'warning', label: '已取消', icon: CircleClose },
  PARTIAL:  { type: 'warning', label: '部分成功', icon: CircleClose },
}

function fmtDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  // 只显示月日 时:分
  const d = new Date(dateStr)
  const month = d.getMonth() + 1
  const day = d.getDate()
  const hour = d.getHours().toString().padStart(2, '0')
  const min = d.getMinutes().toString().padStart(2, '0')
  return `${month}/${day} ${hour}:${min}`
}
</script>

<template>
  <el-card shadow="hover" class="mid-card" :body-style="{ padding: '0' }">
    <template #header>
      <div class="card-header">
        <span class="card-title">
          <el-icon><Timer /></el-icon>
          近期任务
        </span>
      </div>
    </template>
    <el-table :data="jobs" v-loading="loading" stripe size="small">
      <el-table-column label="任务名" prop="job_name" min-width="140" />
      <el-table-column label="交易日期" width="100">
        <template #default="{ row }">
          <span class="mono-text">{{ row.biz_date ?? '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag
            :type="statusConfig[row.status]?.type ?? 'info'"
            size="small"
            effect="light"
          >
            {{ statusConfig[row.status]?.label ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="耗时" width="80" align="right">
        <template #default="{ row }">
          <span class="mono-text text-muted">{{ formatDuration(row.duration_ms) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="开始时间" width="110">
        <template #default="{ row }">
          <span class="mono-text text-muted">{{ fmtDate(row.start_time) }}</span>
        </template>
      </el-table-column>
    </el-table>
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

.mono-text {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
}

.text-muted {
  color: var(--color-text-muted);
}
</style>