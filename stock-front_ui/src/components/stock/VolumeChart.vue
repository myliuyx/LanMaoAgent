<script setup lang="ts">
/**
 * VolumeChart.vue — 成交量图表
 * 使用 ECharts 渲染柱状图，支持与 KLineChart 十字光标联动
 * 依赖：echarts (按需引入)
 */
import { ref, onMounted, onUnmounted, watch, shallowRef } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { StockDaily } from '@/types/stock'

// 注册 ECharts 组件
echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, DataZoomComponent, LegendComponent, CanvasRenderer])

const props = withDefaults(defineProps<{
  /** 行情数据 */
  data?: StockDaily[]
  /** 高度（px） */
  height?: number
  /** 是否显示 MA5 均线 */
  showMA?: boolean
  /** 上涨颜色 */
  upColor?: string
  /** 下跌颜色 */
  downColor?: string
}>(), {
  data: () => [],
  height: 200,
  showMA: true,
  upColor: '#ef4444',
  downColor: '#22c55e',
})

const emit = defineEmits<{
  click: [data: StockDaily]
}>()

const chartRef = ref<HTMLDivElement | null>(null)
const chart = shallowRef<echarts.ECharts | null>(null)

/** 计算 MA */
function calcMA(data: StockDaily[], period: number): (number | null)[] {
  return data.map((_, i) => {
    if (i < period - 1) return null
    const slice = data.slice(i - period + 1, i + 1)
    const avg = slice.reduce((sum, d) => sum + (d.volume ?? 0), 0) / period
    return Math.round(avg)
  })
}

/** 构建 ECharts 选项 */
function buildOptions(): any {
  const dates = props.data.map(d => d.trade_date)
  const volumes = props.data.map(d => ({
    value: d.volume ?? 0,
    itemStyle: {
      color: d.close >= d.open ? props.upColor : props.downColor,
    },
  }))

  const series: any[] = [
    {
      type: 'bar',
      name: '成交量',
      data: volumes,
      barMaxWidth: 12,
    },
  ]

  if (props.showMA) {
    series.push({
      type: 'line',
      name: 'MA5',
      data: calcMA(props.data, 5),
      smooth: false,
      symbol: 'none',
      lineStyle: { width: 1, color: '#f59e0b' },
      z: 10,
    })
  }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any[]) => {
        if (!Array.isArray(params) || params.length === 0) return ''
        const date = params[0].axisValue
        const vol = params.find(p => p.seriesName === '成交量')
        const ma = params.find(p => p.seriesName === 'MA5')
        let html = `<div style="font-weight:600">${date}</div>`
        if (vol) html += `<div>成交量: ${Number(vol.value).toLocaleString()}</div>`
        if (ma && ma.value != null) html += `<div>MA5: ${Number(ma.value).toLocaleString()}</div>`
        return html
      },
    },
    legend: {
      show: props.showMA,
      top: 0,
      right: 0,
      icon: 'circle',
      itemWidth: 8,
      textStyle: { fontSize: 11 },
    },
    grid: { left: 12, right: 10, top: props.showMA ? 30 : 10, bottom: 24 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisTick: { show: false },
      axisLabel: { fontSize: 10, color: '#6b7280' },
    },
    yAxis: {
      type: 'value',
      scale: true,
      splitLine: { lineStyle: { color: '#f3f4f6', type: 'dashed' } },
      axisLabel: { show: false },
    },
    series,
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: 0,
        start: 0,
        end: 100,
      },
    ],
  }
}

/** 初始化图表 */
function initChart() {
  if (!chartRef.value) return
  chart.value = echarts.init(chartRef.value, undefined, { renderer: 'canvas' })
  chart.value.setOption(buildOptions(), false)

  chart.value.on('click', (params: any) => {
    if (!props.data.length) return
    // 直接使用 dataIndex，因为 ECharts bar 的 dataIndex 就是数据数组中的索引
    const idx = params.dataIndex
    if (idx >= 0 && idx < props.data.length) {
      emit('click', props.data[idx])
    }
  })
}

/** 对外方法：设置数据 */
function setData(_newData?: StockDaily[]) {
  if (!chart.value) return
  chart.value.setOption(buildOptions(), true)
}

/** 对外方法：同步十字光标（外部 StockDetailPage 调用） */
function syncCrosshair(params: { dataIndex: number }) {
  if (!chart.value) return
  // 显示 tooltip
  chart.value.dispatchAction({
    type: 'showTip',
    seriesIndex: 0,
    dataIndex: params.dataIndex,
  })
  // 高亮对应柱子
  chart.value.dispatchAction({
    type: 'highlight',
    seriesIndex: 0,
    dataIndex: params.dataIndex,
  })
}

/** 暴露方法 */
defineExpose({ setData, syncCrosshair })

// 监听数据变化
watch(() => props.data, (newData) => {
  if (chart.value && newData && newData.length > 0) {
    chart.value.setOption(buildOptions(), true)
  }
}, { deep: true })

// 响应式 resize
let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  initChart()
  if (chartRef.value) {
    resizeObserver = new ResizeObserver(() => {
      chart.value?.resize()
    })
    resizeObserver.observe(chartRef.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  chart.value?.dispose()
  chart.value = null
})
</script>

<template>
  <div
    ref="chartRef"
    class="volume-chart"
    :style="{ height: `${height}px` }"
  />
</template>

<style scoped>
.volume-chart {
  width: 100%;
}
</style>
