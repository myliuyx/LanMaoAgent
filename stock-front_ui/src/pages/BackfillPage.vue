<script setup lang="ts">
import { ref, shallowRef, onUnmounted } from 'vue'
import {
  ElCard, ElForm, ElFormItem, ElInput, ElSelect, ElOption,
  ElButton, ElMessage, ElProgress,
} from 'element-plus'
import { backfillApi, type BackfillStatus } from '@/api/backfill'

const form = ref({
  symbol: '',
  data_type: 'DAILY' as 'DAILY' | 'FINANCE' | 'ADJUST_FACTOR',
  start_date: '',
  end_date: '',
  force: false,
})

const loading = ref(false)

// 轮询状态
const polling = ref(false)
const pollingInterval = shallowRef<ReturnType<typeof setInterval> | null>(null)
const taskStatus = ref<BackfillStatus | null>(null)

/** 提交表单 */
async function handleSubmit() {
  if (!form.value.symbol.trim()) {
    ElMessage.warning('请输入股票代码')
    return
  }
  function isValidDate(dateStr: string): boolean {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return false
    const d = new Date(dateStr)
    // Date.parse("2023-02-30") 会回绕到 3 月，需逐字段校验
    return d.getFullYear() === parseInt(dateStr.slice(0, 4))
      && d.getMonth() === parseInt(dateStr.slice(5, 7)) - 1
      && d.getDate() === parseInt(dateStr.slice(8, 10))
  }
  if (form.value.start_date && !isValidDate(form.value.start_date)) {
    ElMessage.warning('起始日期无效，请检查月份和日期')
    return
  }
  if (form.value.end_date && !isValidDate(form.value.end_date)) {
    ElMessage.warning('结束日期无效，请检查月份和日期')
    return
  }

  loading.value = true
  stopPolling()
  taskStatus.value = null
  try {
    const res = await backfillApi.run({
      symbol: form.value.symbol.trim(),
      data_type: form.value.data_type,
      start_date: form.value.start_date || undefined,
      end_date: form.value.end_date || undefined,
      force: form.value.force,
    })
    const result = res.data
    ElMessage.success(`任务已提交，任务ID: ${result.task_id}`)
    // 开始轮询状态
    startPolling(result.task_id)
  } catch {
    // 错误已在拦截器处理
  } finally {
    loading.value = false
  }
}

/** 开始轮询 */
function startPolling(taskId: number) {
  polling.value = true
  taskStatus.value = null
  pollingInterval.value = setInterval(async () => {
    try {
      const res = await backfillApi.getStatus(taskId)
      const status = res.data
      taskStatus.value = status
      if (status.status === 'SUCCESS' || status.status === 'FAILED' || status.status === 'CANCELLED') {
        stopPolling()
        if (status.status === 'SUCCESS') {
          ElMessage.success('补数任务执行成功')
        } else if (status.status === 'FAILED') {
          ElMessage.error(`补数任务失败: ${status.message}`)
        }
      }
    } catch {
      // ignore
    }
  }, 2000)
}

/** 停止轮询 */
function stopPolling() {
  polling.value = false
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
    pollingInterval.value = null
  }
}

/** 重置 */
function handleReset() {
  stopPolling()
  taskStatus.value = null
  form.value = {
    symbol: '',
    data_type: 'DAILY',
    start_date: '',
    end_date: '',
    force: false,
  }
}

onUnmounted(stopPolling)
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">补历史数据</h2>

    <el-card shadow="hover" style="margin-bottom: 16px">
      <el-form label-width="120px" @submit.prevent="handleSubmit">
        <el-form-item label="股票代码" required>
          <el-input
            v-model="form.symbol"
            placeholder="600519.SH"
            style="width: 280px"
            :disabled="polling"
          />
        </el-form-item>

        <el-form-item label="数据类型" required>
          <el-select v-model="form.data_type" style="width: 200px" :disabled="polling">
            <el-option label="日线行情" value="DAILY" />
            <el-option label="财务指标" value="FINANCE" />
            <el-option label="复权因子" value="ADJUST_FACTOR" />
          </el-select>
        </el-form-item>

        <el-form-item label="起始日期">
          <el-input
            v-model="form.start_date"
            placeholder="选填，例如 2020-01-01"
            style="width: 220px"
            :disabled="polling"
          />
        </el-form-item>

        <el-form-item label="结束日期">
          <el-input
            v-model="form.end_date"
            placeholder="选填，例如 2026-04-18"
            style="width: 220px"
            :disabled="polling"
          />
        </el-form-item>

        <el-form-item label="强制覆盖">
          <el-select v-model="form.force" style="width: 120px" :disabled="polling">
            <el-option label="否" :value="false" />
            <el-option label="是" :value="true" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit">
            提交补数任务
          </el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 轮询进度 -->
    <el-card v-if="polling || taskStatus" shadow="hover">
      <template #header>
        <div class="card-header">
          任务状态
          <el-tag
            v-if="taskStatus"
            size="small"
            :type="taskStatus.status === 'SUCCESS' ? 'success' : taskStatus.status === 'FAILED' ? 'danger' : 'warning'"
            style="margin-left: 8px"
          >
            {{ taskStatus.status === 'PENDING' ? '排队中' : taskStatus.status === 'RUNNING' ? '运行中' : taskStatus.status === 'SUCCESS' ? '成功' : taskStatus.status === 'FAILED' ? '失败' : taskStatus.status }}
          </el-tag>
        </div>
      </template>

      <el-progress
        v-if="taskStatus"
        :percentage="Math.min(taskStatus.progress ?? 0, 100)"
        :status="taskStatus.status === 'SUCCESS' ? 'success' : taskStatus.status === 'FAILED' ? 'exception' : undefined"
        :stroke-width="12"
        style="margin-bottom: 12px"
      />

      <div v-if="taskStatus?.message" style="font-size: 13px; color: #606266">
        {{ taskStatus.message }}
      </div>

      <div v-if="polling && !taskStatus" style="color: #909399; font-size: 13px">
        正在获取任务状态...
      </div>
    </el-card>
  </div>
</template>
