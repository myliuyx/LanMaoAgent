<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  ElCard, ElTable, ElTableColumn, ElTag, ElPagination,
  ElButton, ElMessage, ElMessageBox,
} from 'element-plus'
import { Delete, Refresh, Rank, Finished } from '@element-plus/icons-vue'
import { watchlistApi } from '@/api/watchlist'
import type { WatchlistItem } from '@/types/watchlist'
import { formatNumber, formatPercent, getChangeColor, getExchangeLabel, getScoreType, getPercentileType, getDistColor, getPEType, getPBType, getVsMA5Color, formatPercentile, formatDist, formatMA5, formatVsMA5, formatAmplitude, formatPE } from '@/utils/format'
import BaseEmpty from '@/components/base/BaseEmpty.vue'

const router = useRouter()

const tableData = ref<WatchlistItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const loading = ref(false)

// 编辑模式
const isEditMode = ref(false)
const dragIndex = ref<number | null>(null)

const hasData = computed(() => tableData.value.length > 0)

// localStorage key
const ORDER_KEY = 'watchlist-order'

function loadOrder(): string[] {
  try {
    const raw = localStorage.getItem(ORDER_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveOrder(order: string[]) {
  localStorage.setItem(ORDER_KEY, JSON.stringify(order))
}

function applyOrder(items: WatchlistItem[]): WatchlistItem[] {
  const savedOrder = loadOrder()
  if (savedOrder.length === 0) return items
  const orderMap = new Map(savedOrder.map((s, i) => [s, i]))
  return [...items].sort((a, b) => {
    const ai = orderMap.get(a.symbol) ?? Infinity
    const bi = orderMap.get(b.symbol) ?? Infinity
    return ai - bi
  })
}

function syncOrderToStorage() {
  saveOrder(tableData.value.map(item => item.symbol))
}

// 从 localStorage 中移除已删除的 symbol
function cleanupOrder(deletedSymbol: string) {
  const savedOrder = loadOrder()
  const cleaned = savedOrder.filter(s => s !== deletedSymbol)
  saveOrder(cleaned)
}

onMounted(() => {
  fetchData()
})

async function fetchData() {
  loading.value = true
  try {
    const res = await watchlistApi.getList({
      page: page.value,
      page_size: pageSize.value,
    })
    const list = res.data?.list ?? []
    total.value = res.data?.total ?? 0
    tableData.value = applyOrder(list)
  } catch {
    ElMessage.error('加载自选股列表失败')
  } finally {
    loading.value = false
  }
}

function toggleEditMode() {
  if (isEditMode.value) {
    // 退出编辑模式，保存当前顺序
    isEditMode.value = false
    syncOrderToStorage()
  } else {
    isEditMode.value = true
  }
}

function onDragStart(index: number) {
  dragIndex.value = index
}

function onDragOver(e: DragEvent, index: number) {
  e.preventDefault()
}

function onDrop(e: DragEvent, targetIndex: number) {
  e.preventDefault()
  if (dragIndex.value === null || dragIndex.value === targetIndex) return
  const arr = [...tableData.value]
  const [moved] = arr.splice(dragIndex.value, 1)
  arr.splice(targetIndex, 0, moved)
  tableData.value = arr
  dragIndex.value = null
}

function onDragEnd() {
  dragIndex.value = null
}

function onRowClick(row: WatchlistItem) {
  if (!isEditMode.value) {
    router.push(`/stocks/${row.symbol}`)
  }
}

function onPageChange(p: number) {
  page.value = p
  fetchData()
}

function goToStock(row: WatchlistItem) {
  router.push(`/stocks/${row.symbol}`)
}

// 格式化交易所

async function handleDelete(row: WatchlistItem) {
  try {
    await ElMessageBox.confirm(
      `确认将「${row.name}（${row.symbol}）」从自选列表中移除？`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
  } catch {
    return
  }

  try {
    await watchlistApi.remove(row.symbol)
    ElMessage.success('已从自选列表中移除')
    cleanupOrder(row.symbol)
    fetchData()
  } catch {
    ElMessage.error('删除失败，请重试')
  }
}
</script>

<template>
  <div class="watchlist-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-header__left">
        <span class="page-header__title">我的自选股</span>
        <el-tag v-if="total > 0" type="info" size="small" round>
          共 {{ total }} 只
        </el-tag>
      </div>
      <div class="page-header__right">
        <el-button
          v-if="isEditMode"
          :icon="Finished"
          size="small"
          type="success"
          @click="toggleEditMode"
        >
          完成
        </el-button>
        <el-button
          v-else
          :icon="Rank"
          size="small"
          @click="toggleEditMode"
        >
          编辑
        </el-button>
        <el-button
          :icon="Refresh"
          size="small"
          @click="fetchData"
        >
          刷新
        </el-button>
      </div>
    </div>

    <!-- 表格区域 -->
    <div class="table-card">
      <BaseEmpty
        v-if="!loading && !hasData"
        description="暂无自选股，去添加感兴趣的股票吧"
        :image-size="100"
      />

      <el-table
        v-else
        :data="tableData"
        v-loading="loading"
        stripe
        class="watchlist-table"
        :row-class-name="isEditMode ? 'edit-mode-row' : ''"
        @row-click="onRowClick"
      >
        <!-- 股票代码 -->
        <el-table-column label="代码" width="110" align="center" fixed>
          <template #default="{ row }">
            <span class="symbol-cell">{{ row.symbol }}</span>
          </template>
        </el-table-column>

        <!-- 股票名称 -->
        <el-table-column label="名称" min-width="130" align="center" fixed>
          <template #default="{ row }">
            <div class="name-cell">
              <span class="name-text">{{ row.name }}</span>
              <el-tag size="small" type="info" effect="plain">
                {{ getExchangeLabel(row.exchange) }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <!-- 最新价 -->
        <el-table-column label="最新价" width="100" align="right">
          <template #default="{ row }">
            <span class="price-cell">{{ formatNumber(row.close, 2) }}</span>
          </template>
        </el-table-column>

        <!-- 涨跌幅 -->
        <el-table-column label="涨跌幅" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.change_pct !== null"
              size="small"
              :color="getChangeColor(row.change_pct) === '#F56C6C' ? '#fef0f0' : '#f0f9eb'"
              :style="{ color: getChangeColor(row.change_pct) }"
              effect="light"
            >
              {{ formatPercent(row.change_pct, 2) }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <!-- 分位 -->
        <el-table-column label="52周分位" width="95" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.price_percentile !== null"
              size="small"
              :type="getPercentileType(row.price_percentile)"
              effect="plain"
            >
              {{ formatPercentile(row.price_percentile) }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <!-- 52周高点 -->
        <el-table-column label="52周高" width="95" align="right">
          <template #default="{ row }">
            <span class="text-muted">{{ formatNumber(row.price_52w_high, 2) }}</span>
          </template>
        </el-table-column>

        <!-- 距高点% -->
        <el-table-column label="距高点" width="90" align="center">
          <template #default="{ row }">
            <span
              v-if="row.dist_to_52w_high_pct !== null"
              class="dist-cell"
              :style="{ color: getDistColor(row.dist_to_52w_high_pct, true) }"
            >
              {{ formatDist(row.dist_to_52w_high_pct) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <!-- 52周低点 -->
        <el-table-column label="52周低" width="95" align="right">
          <template #default="{ row }">
            <span class="text-muted">{{ formatNumber(row.price_52w_low, 2) }}</span>
          </template>
        </el-table-column>

        <!-- 距低点% -->
        <el-table-column label="距低点" width="90" align="center">
          <template #default="{ row }">
            <span
              v-if="row.dist_to_52w_low_pct !== null"
              class="dist-cell"
              :style="{ color: getDistColor(row.dist_to_52w_low_pct, false) }"
            >
              {{ formatDist(row.dist_to_52w_low_pct) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <!-- MA5 -->
        <el-table-column label="MA5" width="95" align="right">
          <template #default="{ row }">
            <span class="text-muted">{{ formatMA5(row.ma5) }}</span>
          </template>
        </el-table-column>

        <!-- 距MA5% -->
        <el-table-column label="距MA5" width="90" align="center">
          <template #default="{ row }">
            <span
              v-if="row.price_vs_ma5_pct !== null"
              :style="{ color: getVsMA5Color(row.price_vs_ma5_pct) }"
              class="vs-ma5-cell"
            >
              {{ formatVsMA5(row.price_vs_ma5_pct) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <!-- 振幅 -->
        <el-table-column label="振幅" width="80" align="center">
          <template #default="{ row }">
            <span class="text-muted">{{ formatAmplitude(row.amplitude) }}</span>
          </template>
        </el-table-column>

        <!-- PE TTM -->
        <el-table-column label="PE" width="80" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.pe_ttm !== null"
              size="small"
              :type="getPEType(row.pe_ttm)"
              effect="plain"
            >
              {{ formatPE(row.pe_ttm) }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <!-- PB -->
        <el-table-column label="PB" width="80" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.pb !== null"
              size="small"
              :type="getPBType(row.pb)"
              effect="plain"
            >
              {{ formatPE(row.pb) }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column label="操作" width="70" align="center" fixed="right">
          <template #default="{ row, $index }">
            <div
              v-if="isEditMode"
              class="drag-handle"
              draggable="true"
              @dragstart="onDragStart($index)"
              @dragover="(e) => onDragOver(e, $index)"
              @drop="(e) => onDrop(e, $index)"
              @dragend="onDragEnd"
              title="拖动排序"
            >
              <el-icon><Rank /></el-icon>
            </div>
            <el-button
              v-else
              :icon="Delete"
              type="danger"
              size="small"
              text
              @click.stop="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div v-if="hasData" class="pagination-wrapper">
        <el-pagination
          :current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="onPageChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.watchlist-page {
  padding: 20px 24px;
  min-height: 100%;
}

/* ── 页面头部 ─────────────────────────────────────── */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header__left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-header__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

/* ── 表格卡片 ─────────────────────────────────────── */
.table-card {
  background: white;
  border-radius: 8px;
  padding: 0;
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

/* ── 表格样式 ─────────────────────────────────────── */
.watchlist-table {
  cursor: pointer;
  width: 100%;
}

.watchlist-table.edit-mode-row {
  cursor: default;
}

/* 强制单元格内容居中（居中列） */
.watchlist-table :deep(.el-table__body-wrapper .el-table__body .el-table__row .el-table__cell) {
  text-align: center;
}

/* 居中列的内容容器 */
.watchlist-table :deep(.el-table__body-wrapper .el-table__body .el-table__row .el-table__cell) .cell {
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 右对齐列：最新价、52周高、52周低、MA5 */
.watchlist-table :deep(.el-table__body-wrapper .el-table__body .el-table__row .el-table__cell:nth-child(3)),
.watchlist-table :deep(.el-table__body-wrapper .el-table__body .el-table__row .el-table__cell:nth-child(6)),
.watchlist-table :deep(.el-table__body-wrapper .el-table__body .el-table__row .el-table__cell:nth-child(8)),
.watchlist-table :deep(.el-table__body-wrapper .el-table__body .el-table__row .el-table__cell:nth-child(10)) {
  text-align: right;
}

.watchlist-table :deep(.el-table__body-wrapper .el-table__body .el-table__row .el-table__cell:nth-child(3) .cell),
.watchlist-table :deep(.el-table__body-wrapper .el-table__body .el-table__row .el-table__cell:nth-child(6) .cell),
.watchlist-table :deep(.el-table__body-wrapper .el-table__body .el-table__row .el-table__cell:nth-child(8) .cell),
.watchlist-table :deep(.el-table__body-wrapper .el-table__body .el-table__row .el-table__cell:nth-child(10) .cell) {
  justify-content: flex-end;
}

.symbol-cell {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.name-text {
  font-weight: 500;
  color: var(--color-text-primary);
}

.price-cell {
  font-family: 'Monaco', 'Menlo', monospace;
  font-weight: 600;
  color: var(--color-text-primary);
}

.text-muted {
  color: var(--color-text-muted);
  font-size: 13px;
}

.dist-cell {
  font-size: 12px;
  font-weight: 500;
}

.vs-ma5-cell {
  font-size: 12px;
  font-weight: 500;
}

/* ── 拖拽手柄 ─────────────────────────────────────── */
.drag-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  cursor: grab;
  color: #909399;
  border-radius: 4px;
  transition: background 0.15s, color 0.15s;
}

.drag-handle:hover {
  background: #f5f7fa;
  color: #409eff;
}

.drag-handle:active {
  cursor: grabbing;
}

/* ── 分页 ─────────────────────────────────────────── */
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding: 16px 0 0 0;
  border-top: 1px solid #f1f5f9;
}
</style>