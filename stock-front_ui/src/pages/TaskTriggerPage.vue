<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  ElCard, ElButton, ElForm, ElFormItem, ElInput, ElSelect, ElOption,
  ElMessage, ElMessageBox,
} from 'element-plus'
import { jobApi } from '@/api/job'

const router = useRouter()

// 当前交易日（默认当天）
const today = new Date().toISOString().slice(0, 10)

// 独立任务列表（无定时，纯手动触发）
const MANUAL_TASKS = [
  {
    jobName: 'sync_board',
    label: '板块主数据同步',
    description: '同步全市场板块数据（行业/概念/地域/指数）',
    params: [] as { key: string; label: string; placeholder: string; default?: string }[],
  },
  {
    jobName: 'sync_board_relation',
    label: '股票-板块关系同步',
    description: '同步股票与板块的归属关系',
    params: [],
  },
  {
    jobName: 'sync_financial',
    label: '财务指标同步',
    description: '同步全市场股票财务指标',
    params: [
      { key: 'year', label: '年份', placeholder: '2026', default: String(new Date().getFullYear()) },
      { key: 'quarter', label: '季度', placeholder: '1', default: String(Math.ceil((new Date().getMonth() + 1) / 3)) },
    ],
  },
  {
    jobName: 'sync_adjust_factor',
    label: '复权因子同步',
    description: '同步全市场股票复权因子',
    params: [
      { key: 'trade_date', label: '交易日期', placeholder: today, default: today },
    ],
  },
  {
    jobName: 'sync_trade_calendar',
    label: '交易日历同步',
    description: '同步交易日历（判断非交易日/节假日）',
    params: [],
  },
]

// 定时任务（可手动触发）
const SCHEDULED_TASKS = [
  { jobName: 'security_master_sync', label: '股票主数据同步', time: '周一至周五 18:00' },
  { jobName: 'daily_stock_sync', label: '日线行情同步', time: '周一至周五 19:00' },
  { jobName: 'factor_compute', label: '技术因子计算', time: '周一至周五 20:30' },
  { jobName: 'selection_mart', label: '选股宽表构建', time: '周一至周五 21:30' },
  { jobName: 'cleanup_logs', label: '日志清理', time: '每天 00:05' },
]

// 每个独立任务的参数状态
const manualParams = ref<Record<string, Record<string, string>>>({})
for (const task of MANUAL_TASKS) {
  manualParams.value[task.jobName] = {}
  for (const p of task.params) {
    manualParams.value[task.jobName][p.key] = p.default ?? ''
  }
}

const loading = ref<string | null>(null)

function buildParams(jobName: string): Record<string, unknown> {
  const extra: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(manualParams.value[jobName] ?? {})) {
    if (v) {
      if (k === 'year' || k === 'quarter') {
        extra[k] = Number(v)
      } else {
        extra[k] = v
      }
    }
  }
  return extra
}

async function triggerManual(task: (typeof MANUAL_TASKS)[0]) {
  loading.value = task.jobName
  try {
    const extra = buildParams(task.jobName)
    const res = await jobApi.run({
      job_name: task.jobName,
      force: false,
      ...extra,
    } as any)
    ElMessage.success({ message: `${task.label} 已触发，任务ID: ${res.data?.task_id ?? '成功'}`, duration: 4000 })
  } catch (e: any) {
    ElMessage.error(e?.message ?? '触发失败')
  } finally {
    loading.value = null
  }
}

async function triggerScheduled(task: (typeof SCHEDULED_TASKS)[0]) {
  try {
    await ElMessageBox.confirm(
      `确认手动触发「${task.label}」？\n该任务定时执行时间为 ${task.time}`,
      '确认触发',
      { type: 'info', confirmButtonText: '确认触发', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  loading.value = task.jobName
  try {
    const res = await jobApi.run({ job_name: task.jobName, biz_date: today, force: false })
    ElMessage.success({ message: `${task.label} 已触发，任务ID: ${res.data?.task_id ?? '成功'}`, duration: 4000 })
  } catch (e: any) {
    ElMessage.error(e?.message ?? '触发失败')
  } finally {
    loading.value = null
  }
}

function viewJobs(jobName: string) {
  router.push({ path: '/jobs', query: { job_name: jobName } })
}
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">任务触发</h2>

    <!-- 独立任务 -->
    <ElCard shadow="hover" style="margin-bottom: 16px">
      <template #header>
        <div class="card-header">独立任务（纯手动触发）</div>
      </template>

      <div class="task-list">
        <div v-for="task in MANUAL_TASKS" :key="task.jobName" class="task-row">
          <div class="task-info">
            <div class="task-label">{{ task.label }}</div>
            <div class="task-desc">{{ task.description }}</div>
            <!-- 动态参数 -->
            <div v-if="task.params.length" class="task-params">
              <ElForm label-width="60px" inline>
                <ElFormItem v-for="p in task.params" :key="p.key" :label="p.label">
                  <ElInput
                    v-model="manualParams[task.jobName][p.key]"
                    :placeholder="p.placeholder"
                    style="width: 130px"
                  />
                </ElFormItem>
              </ElForm>
            </div>
          </div>
          <div class="task-actions">
            <ElButton
              type="primary"
              size="small"
              :loading="loading === task.jobName"
              @click="triggerManual(task)"
            >
              触发
            </ElButton>
            <ElButton size="small" @click="viewJobs(task.jobName)">历史</ElButton>
          </div>
        </div>
      </div>
    </ElCard>

    <!-- 定时任务手动触发 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="card-header">定时任务（支持手动触发）</div>
      </template>

      <div class="task-list">
        <div v-for="task in SCHEDULED_TASKS" :key="task.jobName" class="task-row">
          <div class="task-info">
            <div class="task-label">{{ task.label }}</div>
            <div class="task-desc">定时执行：{{ task.time }}</div>
          </div>
          <div class="task-actions">
            <ElButton
              type="primary"
              size="small"
              :loading="loading === task.jobName"
              @click="triggerScheduled(task)"
            >
              触发
            </ElButton>
            <ElButton size="small" @click="viewJobs(task.jobName)">历史</ElButton>
          </div>
        </div>
      </div>
    </ElCard>
  </div>
</template>

<style scoped>
.card-header {
  font-weight: 600;
  font-size: 15px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.task-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
  gap: 16px;
}

.task-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.task-row:first-child {
  padding-top: 0;
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-label {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 2px;
}

.task-desc {
  font-size: 12px;
  color: #909399;
}

.task-params {
  margin-top: 8px;
}

.task-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}
</style>