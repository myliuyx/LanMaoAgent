<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ElCard, ElDescriptions, ElDescriptionsItem, ElTag, ElScrollbar,
  ElButton, ElMessage, ElEmpty,
} from 'element-plus'
import { jobApi } from '@/api/job'
import type { JobItem } from '@/types/job'
import { JOB_STATUS_MAP } from '@/utils/constants'
import { formatDuration, formatDate } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const jobId = Number(route.params.jobId)
if (isNaN(jobId)) {
  router.replace('/jobs')
}

const loading = ref(false)
const jobDetail = ref<JobItem | null>(null)
const logs = ref<string[]>([])
const logsOffset = ref(0)
const logsTotal = ref(0)
const logsLoading = ref(false)
const logsDone = ref(false)
const retryLoading = ref(false)
const scrollbarRef = ref<{ wrap?: HTMLElement } | null>(null)

const LOG_LIMIT = 100

onMounted(async () => {
  loading.value = true
  try {
    const [detailRes, logsRes] = await Promise.all([
      jobApi.getDetail(jobId),
      jobApi.getLogs(jobId, { offset: 0, limit: LOG_LIMIT }),
    ])
    jobDetail.value = detailRes.data
    logs.value = logsRes.data?.logs ?? []
    logsTotal.value = logsRes.data?.total ?? 0
    logsOffset.value = logs.value.length
    logsDone.value = logs.value.length >= logsTotal.value
  } finally {
    loading.value = false
  }
})

/** 加载更多日志（滚动到底部触发） */
async function loadMoreLogs() {
  if (logsDone.value || logsLoading.value) return
  logsLoading.value = true
  try {
    const res = await jobApi.getLogs(jobId, { offset: logsOffset.value, limit: LOG_LIMIT })
    const newLogs: string[] = res.data?.logs ?? []
    logs.value.push(...newLogs)
    logsOffset.value += newLogs.length
    logsDone.value = logsOffset.value >= logsTotal.value
  } catch {
    // 加载失败忽略
  } finally {
    logsLoading.value = false
  }
}

/** 滚动加载更多日志（el-scrollbar 只传 scrollTop，需从 DOM 取 scrollHeight/clientHeight） */
function handleScroll({ scrollTop }: { scrollTop: number; scrollLeft: number }) {
  const wrap = scrollbarRef.value?.wrap
  if (!wrap) return
  if (wrap.scrollHeight - scrollTop - wrap.clientHeight < 50 && !logsDone.value && !logsLoading.value) {
    loadMoreLogs()
  }
}
function getLogClass(line: string): string {
  if (line.startsWith('ERROR') || line.startsWith('error')) return 'log-error'
  if (line.startsWith('WARN') || line.startsWith('warn')) return 'log-warn'
  if (line.startsWith('INFO') || line.startsWith('info')) return 'log-info'
  return ''
}

/** 重跑任务 */
async function handleRetry() {
  if (!jobDetail.value) return
  retryLoading.value = true
  try {
    const res = await jobApi.run({
      job_name: jobDetail.value.job_name,
      biz_date: jobDetail.value.biz_date ?? undefined,
      force: true,
    })
    ElMessage.success(`任务已重跑: ${res.data?.job_name ?? '成功'}`)
    router.push('/jobs')
  } catch (e: any) {
    ElMessage.error(e?.message ?? '重跑失败')
  } finally {
    retryLoading.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">
      <span>任务详情 #{{ jobId }}</span>
      <el-tag
        v-if="jobDetail"
        :type="(JOB_STATUS_MAP[jobDetail.status]?.type ?? 'info') as any"
        style="margin-left: 12px; vertical-align: middle"
      >
        {{ JOB_STATUS_MAP[jobDetail.status]?.label ?? jobDetail.status }}
      </el-tag>
    </h2>

    <!-- 任务基础信息 -->
    <el-card shadow="hover" style="margin-bottom: 16px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="任务ID">{{ jobDetail?.id }}</el-descriptions-item>
        <el-descriptions-item label="任务名称">{{ jobDetail?.job_name }}</el-descriptions-item>
        <el-descriptions-item label="业务日期">{{ jobDetail?.biz_date ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="耗时">
          {{ jobDetail?.duration_ms != null ? formatDuration(jobDetail.duration_ms) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="开始时间">
          {{ jobDetail?.start_time ? formatDate(jobDetail.start_time) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="结束时间">
          {{ jobDetail?.end_time ? formatDate(jobDetail.end_time) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="原始记录数">
          {{ jobDetail?.rows_raw != null ? jobDetail.rows_raw.toLocaleString() : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="写入记录数">
          {{ jobDetail?.rows_written != null ? jobDetail.rows_written.toLocaleString() : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="错误信息" :span="2">
          <span v-if="jobDetail?.error_message" style="color: #f56c6c">
            {{ jobDetail.error_message }}
          </span>
          <span v-else>-</span>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 重跑按钮 -->
      <div style="margin-top: 16px; text-align: right">
        <el-button
          type="primary"
          :loading="retryLoading"
          @click="handleRetry"
        >
          重跑任务
        </el-button>
      </div>
    </el-card>

    <!-- 执行日志 -->
    <el-card shadow="hover">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>执行日志</span>
          <span style="font-size: 12px; color: #909399">
            {{ logs.length }}{{ logsTotal > logs.length ? ` / ${logsTotal}` : '' }} 条
          </span>
        </div>
      </template>

      <el-scrollbar ref="scrollbarRef" height="420px" @scroll="handleScroll">
        <div v-if="logs.length === 0 && !logsLoading" class="empty-state" style="padding: 40px 0">
          <el-empty description="暂无日志" :image-size="80" />
        </div>
        <pre
          v-else
          class="log-container"
        ><code
          v-for="(line, i) in logs"
          :key="i"
          :class="getLogClass(line)"
          class="log-line"
        >{{ line }}</code></pre>
        <div v-if="logsLoading" style="text-align: center; padding: 8px; color: #909399; font-size: 12px">
          加载中...
        </div>
        <div v-if="logsDone && logs.length > 0" style="text-align: center; padding: 8px; color: #c0c4cc; font-size: 12px">
          — 已加载全部 {{ logs.length }} 条日志 —
        </div>
      </el-scrollbar>
    </el-card>
  </div>
</template>

<style scoped>
.log-container {
  margin: 0;
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  line-height: 1.7;
  color: #606266;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
}
.log-line {
  display: block;
}
.log-error {
  color: #f56c6c;
  font-weight: 600;
}
.log-warn {
  color: #e6a23c;
}
.log-info {
  color: #409eff;
}
</style>
