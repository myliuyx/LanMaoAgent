<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, type IChartApi, type ISeriesApi, type CandlestickData, type HistogramData, ColorType } from 'lightweight-charts'
import type { StockDaily } from '@/types/stock'
import { formatNumber, formatPercent } from '@/utils/format'

const props = withDefaults(defineProps<{
  /** K线数据（同 StockDaily） */
  data?: StockDaily[]
  /** 是否显示成交量 */
  showVolume?: boolean
  /** 是否显示网格 */
  showGrid?: boolean
  /** 高度 */
  height?: number
}>(), {
  data: () => [],
  showVolume: true,
  showGrid: true,
  height: 400,
})

const emit = defineEmits<{
  click: [data: StockDaily]
}>()

// DOM ref
const chartContainerRef = ref<HTMLDivElement | null>(null)

// Chart instances
let chart: IChartApi | null = null
let candlestickSeries: ISeriesApi<'Candlestick'> | null = null
let volumeSeries: ISeriesApi<'Histogram'> | null = null

// ResizeObserver
let resizeObserver: ResizeObserver | null = null

// 自定义十字光标 tooltip
const tooltipRef = ref<HTMLDivElement | null>(null)
const tooltipData = ref<StockDaily | null>(null)

function showTooltip(data: StockDaily, x: number, y: number) {
  tooltipData.value = data
  if (!tooltipRef.value || !chartContainerRef.value) return
  const containerRect = chartContainerRef.value.getBoundingClientRect()
  const containerWidth = chartContainerRef.value.clientWidth
  tooltipRef.value.style.display = 'block'
  // 智能定位：避免超出右边界
  const tooltipWidth = 200
  let left = x + 12
  if (left + tooltipWidth > containerWidth - 8) {
    left = x - tooltipWidth - 12
  }
  tooltipRef.value.style.left = `${left}px`
  tooltipRef.value.style.top = `${y - 10}px`
}

function hideTooltip() {
  tooltipData.value = null
  if (tooltipRef.value) tooltipRef.value.style.display = 'none'
}

/** 初始化图表 */
function initChart() {
  if (!chartContainerRef.value) return

  chart = createChart(chartContainerRef.value, {
    width: chartContainerRef.value.clientWidth,
    height: props.height,
    layout: {
      background: { type: ColorType.Solid, color: '#ffffff' },
      attributionLogo: false,
    },
    grid: {
      vertLines: { visible: props.showGrid },
      horzLines: { visible: props.showGrid },
    },
    crosshair: {
      mode: 1, // Normal
    },
    timeScale: {
      timeVisible: true,
      secondsVisible: false,
      borderVisible: true,
    },
    rightPriceScale: {
      borderVisible: true,
    },
    handleScroll: {
      mouseWheel: true,
      pressedMouseMove: true,
    },
    handleScale: {
      axisPressedMouseMove: true,
      mouseWheel: true,
      pinch: true,
    },
    localization: {
      // 解决十字光标悬停时日期显示为 "24 4月 '26 00:00" 的问题
      // timeFormatter 控制十字光标标签的时间格式
      timeFormatter: (time: any) => {
        // time 可能是 UTCTimestamp(number) 或 BusinessDay 对象 { year, month, day }
        let year: number, month: number, day: number
        if (typeof time === 'number') {
          // Unix timestamp (秒)
          const d = new Date(time * 1000)
          year = d.getUTCFullYear()
          month = d.getUTCMonth() + 1
          day = d.getUTCDate()
        } else if (typeof time === 'object' && time !== null) {
          // BusinessDay 对象 { year, month, day } 或 { time: string }
          if ('timestamp' in time) {
            const d = new Date((time as any).timestamp * 1000)
            year = d.getUTCFullYear()
            month = d.getUTCMonth() + 1
            day = d.getUTCDate()
          } else if ('year' in time) {
            year = (time as any).year
            month = (time as any).month
            day = (time as any).day
          } else if ('time' in time) {
            // 字符串格式 "YYYY-MM-DD"
            const parts = (time as any).time.split('-')
            year = parseInt(parts[0])
            month = parseInt(parts[1])
            day = parseInt(parts[2])
          } else {
            return String(time)
          }
        } else {
          return String(time)
        }
        return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
      },
    },
  })

  // 蜡烛图 series — A股 Convention: 红涨(涨) 绿跌(跌)
  candlestickSeries = chart.addCandlestickSeries({
    upColor: '#ef4444',    // 红色涨
    downColor: '#22c55e',  // 绿色跌
    borderUpColor: '#ef4444',
    borderDownColor: '#22c55e',
    wickUpColor: '#ef4444',
    wickDownColor: '#22c55e',
  })

  // 成交量 series（下方）
  if (props.showVolume) {
    volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.92, bottom: 0 } })
  }

  // 注册数据
  if (props.data.length > 0) {
    setData(props.data)
  }

  // 点击事件
  chart.subscribeClick((param) => {
    if (!param.time || !candlestickSeries) return
    const data = param.seriesData.get(candlestickSeries) as CandlestickData | undefined
    if (data && props.data) {
      const found = props.data.find(d => d.trade_date === (data.time as string))
      if (found) emit('click', found)
    }
  })

  // 十字光标移动事件 → 显示自定义 tooltip
  chart.subscribeCrosshairMove((param) => {
    if (!param.time || !candlestickSeries) {
      hideTooltip()
      return
    }
    const candle = param.seriesData.get(candlestickSeries) as CandlestickData | undefined
    if (!candle || !props.data) {
      hideTooltip()
      return
    }
    const found = props.data.find(d => d.trade_date === (candle.time as string))
    if (found && param.point) {
      showTooltip(found, param.point.x, param.point.y)
    } else {
      hideTooltip()
    }
  })

  // 自适应宽度
  resizeObserver = new ResizeObserver(() => {
    if (chart && chartContainerRef.value) {
      chart.applyOptions({ width: chartContainerRef.value.clientWidth })
    }
  })
  resizeObserver.observe(chartContainerRef.value)
}

/** 设置 K 线数据 */
function setData(klineData: StockDaily[]) {
  if (!candlestickSeries) return

  const candleData: CandlestickData[] = klineData.map(d => ({
    time: d.trade_date as CandlestickData['time'],
    open: d.open,
    high: d.high,
    low: d.low,
    close: d.close,
  }))
  candlestickSeries.setData(candleData)

  if (volumeSeries) {
    const volumeData: HistogramData[] = klineData.map(d => ({
      time: d.trade_date as HistogramData['time'],
      value: d.volume ?? 0,
      color: d.close >= d.open ? '#ef4444' : '#22c55e',
    }))
    volumeSeries.setData(volumeData)
  }

  // 自动缩放（数据少于2条时不自动缩放，避免单根K线被撑满填满整个图表导致K线和成交量柱子重叠）
  if (klineData.length > 2) {
    chart?.timeScale().fitContent()
  }
}

/** 重置缩放 */
function resetZoom() {
  chart?.timeScale().fitContent()
}

/** 同步十字光标到指定索引（供 VolumeChart 调用联动） */
function syncCrosshair(params: { dataIndex: number }) {
  if (!chart || !props.data.length) return
  const target = props.data[params.dataIndex]
  if (!target) return
  // 滚动到目标位置
  chart.timeScale().scrollToPosition(params.dataIndex, true)
}

/** 暴露方法给父组件 */
defineExpose({ resetZoom, setData, syncCrosshair })

// Watch data changes
watch(() => props.data, (newData) => {
  if (newData && newData.length > 0) {
    setData(newData)
  }
}, { deep: true })

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  chart?.remove()
  chart = null
  candlestickSeries = null
  volumeSeries = null
})
</script>

<template>
  <div ref="chartContainerRef" class="kline-chart">
    <!-- 自定义十字光标浮窗 -->
    <div ref="tooltipRef" class="kline-tooltip" style="display: none">
      <div v-if="tooltipData" class="kline-tooltip__inner">
        <div class="kline-tooltip__date">{{ tooltipData.trade_date }}</div>
        <div class="kline-tooltip__row">
          <span class="kline-tooltip__label">开盘</span>
          <span class="kline-tooltip__value">{{ formatNumber(tooltipData.open) }}</span>
        </div>
        <div class="kline-tooltip__row">
          <span class="kline-tooltip__label">最高</span>
          <span class="kline-tooltip__value">{{ formatNumber(tooltipData.high) }}</span>
        </div>
        <div class="kline-tooltip__row">
          <span class="kline-tooltip__label">最低</span>
          <span class="kline-tooltip__value">{{ formatNumber(tooltipData.low) }}</span>
        </div>
        <div class="kline-tooltip__row">
          <span class="kline-tooltip__label">收盘</span>
          <span class="kline-tooltip__value">{{ formatNumber(tooltipData.close) }}</span>
        </div>
        <div class="kline-tooltip__row">
          <span class="kline-tooltip__label">换手率</span>
          <span class="kline-tooltip__value">{{ formatPercent(tooltipData.turnover_rate) }}</span>
        </div>
        <div class="kline-tooltip__row">
          <span class="kline-tooltip__label">成交量</span>
          <span class="kline-tooltip__value">{{ formatNumber(tooltipData.volume, 0) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kline-chart {
  width: 100%;
  /* height 由 props 控制，默认 400px */
  position: relative;
}

/* 自定义十字光标浮窗 */
.kline-tooltip {
  position: absolute;
  z-index: 10;
  pointer-events: none;
  background: #1a1a1a;
  border: 1px solid #3a3a3a;
  border-radius: 6px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
  padding: 8px 12px;
  min-width: 160px;
}

.kline-tooltip__inner {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.kline-tooltip__date {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 4px;
  font-weight: 600;
}

.kline-tooltip__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  line-height: 1.4;
}

.kline-tooltip__label {
  color: #9ca3af;
  margin-right: 12px;
}

.kline-tooltip__value {
  color: #f3f4f6;
  font-weight: 500;
  font-family: 'Courier New', monospace;
}
</style>
