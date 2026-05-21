<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElCard, ElTable, ElTableColumn, ElTag, ElInput, ElSelect, ElOption, ElButton, ElPagination } from 'element-plus'
import { coverageApi } from '@/api/coverage'
import type { DataCoverage } from '@/types/stock'
import { DATA_TYPE_MAP } from '@/utils/constants'
import { formatDate } from '@/utils/format'

const router = useRouter()
const tableData = ref<DataCoverage[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const symbol = ref('')
const dataType = ref('')
const loading = ref(false)

onMounted(fetchData)

async function fetchData() {
  loading.value = true
  try {
    const res = await coverageApi.getList({
      symbol: symbol.value || undefined,
      data_type: dataType.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    tableData.value = res.data?.list ?? []
    total.value = res.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchData()
}

function onPageChange(p: number) {
  page.value = p
  fetchData()
}

function goToStockDetail(symbol: string) {
  router.push(`/stocks/${symbol}`)
}
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">数据覆盖</h2>

    <el-card shadow="hover" style="margin-bottom: 12px">
      <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center;">
        <el-input
          v-model="symbol"
          placeholder="股票代码"
          style="width: 180px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select v-model="dataType" style="width: 140px" clearable placeholder="数据类型" @change="handleSearch">
          <el-option label="日线行情" value="DAILY" />
          <el-option label="财务指标" value="FINANCE" />
          <el-option label="复权因子" value="ADJUST_FACTOR" />
          <el-option label="技术因子" value="FACTOR" />
        </el-select>
        <el-button type="primary" @click="handleSearch">查询</el-button>
      </div>
    </el-card>

    <el-card shadow="hover">
      <el-table
        border
        style="width: 100%; table-layout: fixed"
        :data="tableData"
        stripe
        :loading="loading"
        row-class-name="clickable-row"
        @row-click="(row) => goToStockDetail(row.symbol)"
      >
        <el-table-column prop="symbol" label="股票代码" width="120" />
        <el-table-column prop="name" label="股票名称" min-width="120" />
        <el-table-column prop="data_type" label="数据类型" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="row.data_type === 'DAILY' ? 'primary' : row.data_type === 'FINANCE' ? 'success' : 'warning'">
              {{ DATA_TYPE_MAP[row.data_type]?.label ?? row.data_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_date" label="开始日期" width="120">
          <template #default="{ row }">
            {{ row.start_date ? formatDate(row.start_date) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="end_date" label="结束日期" width="120">
          <template #default="{ row }">
            {{ row.end_date ? formatDate(row.end_date) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="is_full_history" label="完整历史" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_full_history ? 'success' : 'info'" size="small">
              {{ row.is_full_history ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_sync_at" label="最后同步">
          <template #default="{ row }">
            {{ row.last_sync_at ? formatDate(row.last_sync_at) : '-' }}
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
  </div>
</template>

<style scoped>
:deep(.clickable-row) {
  cursor: pointer;
}
</style>
