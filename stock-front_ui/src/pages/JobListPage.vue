<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  ElCard, ElTable, ElTableColumn, ElTag, ElPagination,
  ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElMessage,
  ElRadioGroup, ElRadioButton,
} from 'element-plus'
import { jobApi } from '@/api/job'
import type { JobItem, JobStatus } from '@/types/job'
import { JOB_STATUS_MAP } from '@/utils/constants'
import { formatDuration, formatDate } from '@/utils/format'

const router = useRouter()

// 数据
const tableData = ref<JobItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const loading = ref(false)

// 状态筛选
const currentStatus = ref<JobStatus | ''>('')

const STATUS_TABS: { label: string; value: JobStatus | '' }[] = [
  { label: '全部', value: '' },
  { label: '排队中', value: 'PENDING' },
  { label: '运行中', value: 'RUNNING' },
  { label: '成功', value: 'SUCCESS' },
  { label: '失败', value: 'FAILED' },
  { label: '已取消', value: 'CANCELLED' },
]

// 手动触发弹窗
const triggerVisible = ref(false)
const triggerForm = ref({ job_name: '', biz_date: '', force: false })
const triggerLoading = ref(false)

onMounted(() => {
  fetchData()
})

async function fetchData() {
  loading.value = true
  try {
    const res = await jobApi.getList({
      status: currentStatus.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    // 后端返回 {code, message, data: {list, total}}
    tableData.value = res.data?.list ?? []
    total.value = res.data?.total ?? 0
  } catch {
    ElMessage.error('加载任务列表失败')
  } finally {
    loading.value = false
  }
}

function onStatusChange(status: string) {
  currentStatus.value = status as JobStatus | ''
  page.value = 1
  fetchData()
}

function onPageChange(p: number) {
  page.value = p
  fetchData()
}

function goToJobDetail(job: JobItem) {
  router.push(`/jobs/${job.id}`)
}

async function handleCancel(job: JobItem) {
  try {
    await jobApi.cancel(job.id)
    ElMessage.success('任务已取消')
    fetchData()
  } catch {
    ElMessage.error('取消失败，请重试')
  }
}

async function handleTrigger() {
  if (!triggerForm.value.job_name.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  triggerLoading.value = true
  try {
    const res = await jobApi.run({
      job_name: triggerForm.value.job_name.trim(),
      biz_date: triggerForm.value.biz_date || undefined,
      force: triggerForm.value.force,
    })
    ElMessage.success(`任务已触发: ${res.data?.task_id ?? '成功'}`)
    triggerVisible.value = false
    triggerForm.value = { job_name: '', biz_date: '', force: false }
    page.value = 1
    fetchData()
  } catch (e: any) {
    ElMessage.error(e?.message ?? '触发失败')
  } finally {
    triggerLoading.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">任务管理</h2>

    <el-card shadow="hover" style="margin-bottom: 12px">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px">
        <!-- 状态筛选 tabs -->
        <el-radio-group :model-value="currentStatus" size="default" @update:model-value="(v) => onStatusChange(v as any)">
          <el-radio-button v-for="tab in STATUS_TABS" :key="tab.value" :value="tab.value">
            {{ tab.label }}
          </el-radio-button>
        </el-radio-group>

        <!-- 手动触发按钮 -->
        <el-button type="primary" @click="triggerVisible = true">
          手动触发任务
        </el-button>
      </div>
    </el-card>

    <!-- 任务列表 -->
    <el-card shadow="hover">
      <el-table
        border
        style="width: 100%; table-layout: fixed"
        :data="tableData"
        stripe
        :loading="loading"
        row-class-name="clickable-row"
        @row-click="(row) => goToJobDetail(row)"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="job_name" label="任务名称" min-width="180" />
        <el-table-column prop="biz_date" label="业务日期" width="110" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="(JOB_STATUS_MAP[row.status]?.type ?? 'info') as any" size="small">
              {{ JOB_STATUS_MAP[row.status]?.label ?? row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="170">
          <template #default="{ row }">
            {{ row.start_time ? formatDate(row.start_time) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="end_time" label="结束时间" width="170">
          <template #default="{ row }">
            {{ row.end_time ? formatDate(row.end_time) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="duration_ms" label="耗时" width="90">
          <template #default="{ row }">
            {{ row.duration_ms != null ? formatDuration(row.duration_ms) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="rows_written" label="写入条数" width="110" align="right">
          <template #default="{ row }">
            {{ row.rows_written != null ? row.rows_written.toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="200">
          <template #default="{ row }">
            <span v-if="row.error_message" style="color: #f56c6c; font-size: 12px">
              {{ row.error_message }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'PENDING' || row.status === 'RUNNING'"
              type="danger"
              size="small"
              link
              @click.stop="handleCancel(row)"
            >
              取消
            </el-button>
            <span v-else style="color: #c0c4cc; font-size: 12px">-</span>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end"
        @current-change="onPageChange"
        @size-change="() => { page = 1; fetchData() }"
      />
    </el-card>

    <!-- 手动触发弹窗 -->
    <el-dialog v-model="triggerVisible" title="手动触发任务" width="440px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="任务名称" required>
          <el-input
            v-model="triggerForm.job_name"
            placeholder="例如: daily_stock_crawler"
            @keyup.enter="handleTrigger"
          />
        </el-form-item>
        <el-form-item label="业务日期">
          <el-input
            v-model="triggerForm.biz_date"
            placeholder="选填，例如: 2026-04-18"
          />
        </el-form-item>
        <el-form-item label="强制重跑">
          <el-radio-group v-model="triggerForm.force">
            <el-radio-button :value="false">否</el-radio-button>
            <el-radio-button :value="true">是</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="triggerVisible = false">取消</el-button>
        <el-button type="primary" :loading="triggerLoading" @click="handleTrigger">确认触发</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
:deep(.clickable-row) {
  cursor: pointer;
}
</style>
