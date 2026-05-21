<script setup lang="ts">
/**
 * VirtualTable — 虚拟滚动表格
 * 用于大数据量（>500 条）场景，避免一次性渲染大量 DOM
 * 使用 vue-virtual-scroller 的 RecycleScroller
 */
// @ts-ignore vue-virtual-scroller has no types
import { RecycleScroller } from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'

export interface VirtualTableColumn {
  prop: string
  label: string
  width?: number | string
  align?: 'left' | 'center' | 'right'
  formatter?: (row: Record<string, any>, col: VirtualTableColumn) => string
}

const props = withDefaults(
  defineProps<{
    data: Record<string, any>[]
    columns: VirtualTableColumn[]
    itemHeight?: number
    height?: number
    rowClassName?: string
  }>(),
  {
    itemHeight: 44,
    height: 400,
    rowClassName: '',
  }
)

const emit = defineEmits<{
  'row-click': [row: Record<string, any>]
}>()

function formatCell(row: Record<string, any>, col: VirtualTableColumn): string {
  if (col.formatter) return col.formatter(row, col)
  const val = row[col.prop]
  if (val == null) return '-'
  return String(val)
}

function getColStyle(col: VirtualTableColumn) {
  const style: Record<string, string> = {}
  if (col.width) style.width = typeof col.width === 'number' ? `${col.width}px` : String(col.width)
  if (col.align) style.textAlign = col.align
  return style
}
</script>

<template>
  <div class="virtual-table-wrap">
    <!-- 表头 -->
    <div class="vt-header">
      <div
        v-for="col in props.columns"
        :key="col.prop"
        class="vt-th"
        :style="getColStyle(col)"
      >
        {{ col.label }}
      </div>
    </div>

    <!-- 虚拟滚动体 -->
    <RecycleScroller
      :items="props.data"
      :item-size="props.itemHeight"
      key-field="symbol"
      class="vt-scroller"
      :buffer="200"
    >
      <template #default="{ item, index }">
        <div
          class="vt-row"
          :class="[props.rowClassName, index % 2 === 0 ? 'vt-row--even' : 'vt-row--odd']"
          :style="{ height: `${props.itemHeight}px` }"
          @click="emit('row-click', item)"
        >
          <div
            v-for="col in props.columns"
            :key="col.prop"
            class="vt-cell"
            :style="getColStyle(col)"
          >
            <slot :name="`cell-${col.prop}`" :row="item" :value="item[col.prop]">
              {{ formatCell(item, col) }}
            </slot>
          </div>
        </div>
      </template>
    </RecycleScroller>

    <!-- 空状态 -->
    <div v-if="props.data.length === 0" class="vt-empty">
      暂无数据
    </div>
  </div>
</template>

<style scoped>
.virtual-table-wrap {
  display: flex;
  flex-direction: column;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  overflow: hidden;
  font-size: 14px;
  color: #606266;
}

.vt-header {
  display: flex;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
  font-weight: 600;
  font-size: 13px;
  color: #303133;
  position: sticky;
  top: 0;
  z-index: 1;
}

.vt-th {
  flex: 1;
  padding: 12px 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.vt-scroller {
  height: v-bind('props.height + "px"');
}

.vt-row {
  display: flex;
  align-items: center;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid #f0f0f0;
}

.vt-row:hover {
  background: #ecf5ff;
}

.vt-row--odd {
  background: #fafafa;
}

.vt-row--even {
  background: #ffffff;
}

.vt-row:hover.vt-row--odd {
  background: #ecf5ff;
}

.vt-cell {
  flex: 1;
  padding: 0 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.vt-empty {
  padding: 48px;
  text-align: center;
  color: #909399;
  font-size: 14px;
}
</style>
