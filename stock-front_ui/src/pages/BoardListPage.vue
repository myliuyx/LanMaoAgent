<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElCard, ElTable, ElTableColumn, ElTag, ElInput, ElPagination, ElRadioGroup, ElRadioButton } from 'element-plus'
import { boardApi } from '@/api/board'
import type { BoardItem } from '@/types/board'
import { BOARD_TYPE_MAP } from '@/utils/constants'

const router = useRouter()

const tableData = ref<BoardItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const keyword = ref('')
const boardType = ref('')
const loading = ref(false)

const BOARD_TYPE_TABS: { label: string; value: string }[] = [
  { label: '全部', value: '' },
  { label: '行业', value: 'INDUSTRY' },
  { label: '概念', value: 'CONCEPT' },
  { label: '指数', value: 'INDEX' },
  { label: '地域', value: 'AREA' },
]

onMounted(() => {
  fetchData()
})

onUnmounted(() => {
  listAbort?.abort()
})

let listAbort: AbortController | null = null

async function fetchData() {
  listAbort?.abort()
  listAbort = new AbortController()
  loading.value = true
  try {
    const res = await boardApi.getList({
      board_type: boardType.value || undefined,
      keyword: keyword.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    }, listAbort.signal)
    tableData.value = res.data?.list ?? []
    total.value = res.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function onTypeChange(type: string) {
  boardType.value = type
  page.value = 1
  fetchData()
}

function onKeywordSearch() {
  page.value = 1
  fetchData()
}

function onPageChange(p: number) {
  page.value = p
  fetchData()
}

function goToBoardDetail(row: BoardItem) {
  router.push(`/boards/${row.board_code}`)
}
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">板块分析</h2>

    <!-- 筛选工具栏 -->
    <el-card shadow="hover" style="margin-bottom: 12px">
      <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: space-between">
        <!-- 板块类型 tabs -->
        <el-radio-group :model-value="boardType" @update:model-value="(v) => onTypeChange(v as any)">
          <el-radio-button v-for="tab in BOARD_TYPE_TABS" :key="tab.value" :value="tab.value">
            {{ tab.label }}
          </el-radio-button>
        </el-radio-group>

        <!-- 关键词搜索 -->
        <el-input
          v-model="keyword"
          placeholder="搜索板块名称"
          style="width: 240px"
          clearable
          @keyup.enter="onKeywordSearch"
          @clear="onKeywordSearch"
        />
      </div>
    </el-card>

    <!-- 板块列表 -->
    <el-card shadow="hover">
      <el-table
        border
        style="width: 100%; table-layout: fixed"
        :data="tableData"
        stripe
        :loading="loading"
        row-class-name="clickable-row"
        @row-click="goToBoardDetail"
      >
        <el-table-column prop="board_code" label="板块代码" width="120" />
        <el-table-column prop="board_name" label="板块名称" min-width="180" />
        <el-table-column prop="board_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.board_type === 'INDUSTRY' ? 'primary' : row.board_type === 'CONCEPT' ? 'success' : row.board_type === 'INDEX' ? 'warning' : 'info'">
              {{ BOARD_TYPE_MAP[row.board_type]?.label ?? row.board_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="member_count" label="成分股数" width="100" align="right">
          <template #default="{ row }">
            {{ row.member_count != null ? row.member_count.toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '活跃' : '不活跃' }}
            </el-tag>
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
