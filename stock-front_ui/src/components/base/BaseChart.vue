<script setup lang="ts">
/**
 * BaseChart.vue — ECharts 统一封装组件
 * 解决 VolumeChart 等组件里重复手写的 init/dispose/resize 逻辑
 */
import { ref, onMounted, onUnmounted, watch, shallowRef } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, CandlestickChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

// 注册 ECharts 组件（最基础的组件集，覆盖大多数场景）
// 使用标志位避免多实例重复注册（<script setup> 每次实例化都会执行）
const _echartsKey = '__echarts_base_registered__' as never
if (!(echarts as Record<string, unknown>)[_echartsKey]) {
  echarts.use([
    BarChart,
    LineChart,
    CandlestickChart,
    GridComponent,
    TooltipComponent,
    LegendComponent,
    DataZoomComponent,
    CanvasRenderer,
  ])
  ;(echarts as Record<string, unknown>)[_echartsKey] = true
}

const props = withDefaults(defineProps<{
  /** ECharts 选项（computed 或 direct object） */
  options: any
  /** 高度（px），默认 300 */
  height?: number
  /** 是否自动监听容器 resize（默认 true） */
  autoResize?: boolean
}>(), {
  height: 300,
  autoResize: true,
})

const containerRef = ref<HTMLDivElement | null>(null)
const chart = shallowRef<echarts.ECharts | null>(null)

/** 初始化图表 */
function initChart() {
  if (!containerRef.value) return
  if (props.options == null) return  // 等待有效 options 再初始化
  chart.value = echarts.init(containerRef.value, undefined, { renderer: 'canvas' })
  chart.value.setOption(props.options)
}

/** 对外方法：手动设置选项 */
function setOption(opts: any, notMerge = false) {
  chart.value?.setOption(opts, notMerge)
}

/** 对外方法：手动触发 resize */
function resize() {
  chart.value?.resize()
}

/** 对外方法：获取 ECharts 实例 */
function getInstance(): echarts.ECharts | null {
  return chart.value
}

defineExpose({ setOption, resize, getInstance })

// 监听 options 变化，自动 setOption（notMerge = true）
watch(
  () => props.options,
  (newOptions) => {
    if (!newOptions) return
    if (!chart.value) {
      // chart 尚未初始化（可能是 options 初始为 null，现在变为有效值）
      initChart()
      return
    }
    chart.value.setOption(newOptions, true)
  },
)

// ResizeObserver
let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  initChart()
  if (props.autoResize && containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      chart.value?.resize()
    })
    resizeObserver.observe(containerRef.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  chart.value?.dispose()
  chart.value = null
})
</script>

<template>
  <div
    ref="containerRef"
    class="base-chart"
    :style="{ height: `${height}px` }"
  />
</template>

<style scoped>
.base-chart {
  width: 100%;
}
</style>
