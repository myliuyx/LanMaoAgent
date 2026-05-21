<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElCard, ElTable, ElTableColumn, ElTag, ElPagination } from 'element-plus'
import { boardApi } from '@/api/board'
import type { BoardDetail, BoardMember } from '@/types/board'
import { BOARD_TYPE_MAP } from '@/utils/constants'
import { formatPercent } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const boardCode = route.params.boardCode as string

const boardDetail = ref<BoardDetail | null>(null)
const members = ref<BoardMember[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const sortBy = ref('change_pct')
const sortOrder = ref<'asc' | 'desc'>('desc')
const loading = ref(false)
let detailAbort: AbortController | null = null
let membersAbort: AbortController | null = null

onMounted(() => {
  fetchDetail()
  fetchMembers()
})

async function fetchDetail() {
  detailAbort?.abort()
  detailAbort = new AbortController()
  try {
    const res = await boardApi.getDetail(boardCode, detailAbort.signal)
    boardDetail.value = res.data
  } catch {
    // ignore (aborted or network error)
  }
}

async function fetchMembers() {
  membersAbort?.abort()
  membersAbort = new AbortController()
  loading.value = true
  try {
    const res = await boardApi.getMembers(boardCode, {
      page: page.value,
      page_size: pageSize.value,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
      signal: membersAbort.signal,
    })
    members.value = res.data?.list ?? []
    total.value = res.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function onSortChange({ prop, order }: { prop: string; order: string }) {
  sortBy.value = prop || 'change_pct'
  sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  page.value = 1
  fetchMembers()
}

onUnmounted(() => {
  detailAbort?.abort()
  membersAbort?.abort()
})

function onPageChange(p: number) {
  page.value = p
  fetchMembers()
}

function goToStockDetail(row: BoardMember) {
  router.push(`/stocks/${row.symbol}`)
}
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">
      {{ boardDetail?.board_name ?? boardCode }}
      <el-tag
        v-if="boardDetail"
        size="small"
        style="margin-left: 10px; vertical-align: middle"
      >
        {{ BOARD_TYPE_MAP[boardDetail.board_type]?.label ?? boardDetail.board_type }}
      </el-tag>
    </h2>

    <!-- 板块基本信息 -->
    <el-card shadow="hover" style="margin-bottom: 16px">
      <div style="display: flex; gap: 24px; align-items: center; flex-wrap: wrap">
        <div>板块代码：<strong>{{ boardDetail?.board_code ?? '-' }}</strong></div>
        <div>成分股数量：<strong>{{ total }}</strong></div>
        <div>状态：
          <el-tag :type="boardDetail?.is_active ? 'success' : 'info'" size="small">
            {{ boardDetail?.is_active ? '活跃' : '不活跃' }}
          </el-tag>
        </div>
      </div>
    </el-card>

    <!-- 成分股列表 -->
    <el-card shadow="hover">
      <el-table
        border
        style="width: 100%; table-layout: fixed"
        :data="members"
        stripe
        :loading="loading"
        row-class-name="clickable-row"
        @sort-change="onSortChange"
        @row-click="goToStockDetail"
      >
        <el-table-column prop="symbol" label="代码" width="110" :sortable="('custom' as any)" />
        <el-table-column prop="name" label="名称" min-width="120" show-overflow-tooltip />
        <el-table-column prop="exchange" label="交易所" width="70" />
        <el-table-column prop="industry_l1" label="行业" min-width="120" show-overflow-tooltip />
        <el-table-column prop="close" label="收盘价" width="100" align="right" :sortable="('custom' as any)">
          <template #default="{ row }">
            {{ row.close?.toFixed(2) ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="change_pct" label="涨跌幅" width="100" align="right" :sortable="('custom' as any)">
          <template #default="{ row }">
            <span :class="row.change_pct > 0 ? 'text-rise' : row.change_pct < 0 ? 'text-fall' : ''">
              {{ formatPercent(row.change_pct) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="turnover_rate" label="换手率" width="90" align="right" :sortable="('custom' as any)">
          <template #default="{ row }">
            {{ formatPercent(row.turnover_rate) }}
          </template>
        </el-table-column>
        <el-table-column prop="market_value" label="总市值" width="110" align="right">
          <template #default="{ row }">
            {{ row.market_value
              ? (row.market_value >= 1e8
                  ? (row.market_value / 1e8).toFixed(2) + '亿'
                  : (row.market_value / 1e4).toFixed(0) + '万')
              : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="trend_score" label="趋势评分" width="100" align="right" :sortable="('custom' as any)">
          <template #default="{ row }">
            {{ row.trend_score?.toFixed(1) ?? '-' }}
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
        @size-change="() => { page = 1; fetchMembers() }"
      />
    </el-card>
  </div>
</template>

<style scoped>
:deep(.clickable-row) {
  cursor: pointer;
}
</style>
