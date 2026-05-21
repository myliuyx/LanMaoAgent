<script setup lang="ts">
import { computed } from 'vue'
import { ElButton, ElTag, ElIcon } from 'element-plus'
import { Star, StarFilled } from '@element-plus/icons-vue'
import type { StockProfile, StockDaily } from '@/types/stock'

const props = defineProps<{
  profile: StockProfile | null
  latestDaily: StockDaily | null
  inWatchlist: boolean
  watchlistLoading: boolean
}>()

const emit = defineEmits<{
  toggleWatchlist: []
}>()

const exchangeLabel = computed(() => {
  const ex = props.profile?.exchange
  if (ex === 'SH') return '上交所'
  if (ex === 'SZ') return '深交所'
  if (ex === 'BJ') return '北交所'
  return ex ?? '-'
})

function formatVol(v: number) {
  if (v == null || v === 0) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + ' 亿'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + ' 万'
  return String(v)
}
</script>

<template>
  <div class="stock-header">
    <div class="stock-header__left">
      <div class="stock-name-row">
        <div class="stock-name">{{ profile?.name ?? '-' }}</div>
        <el-button
          class="watchlist-btn"
          :type="inWatchlist ? 'warning' : 'default'"
          size="small"
          :loading="watchlistLoading"
          @click="emit('toggleWatchlist')"
        >
          <el-icon>
            <StarFilled v-if="inWatchlist" />
            <Star v-else />
          </el-icon>
          {{ inWatchlist ? '已自选' : '加入自选' }}
        </el-button>
      </div>
      <div class="stock-meta">
        <span class="stock-meta__item">{{ profile?.symbol ?? '-' }}</span>
        <span class="stock-meta__sep">·</span>
        <span class="stock-meta__item">{{ exchangeLabel }}</span>
        <span class="stock-meta__sep">·</span>
        <span class="stock-meta__item">{{ profile?.industry_l1 ?? '-' }}</span>
      </div>
    </div>
    <div class="stock-header__right">
      <div class="stock-header__date" v-if="latestDaily?.trade_date">
        <el-tag size="small" type="info" effect="plain">{{ latestDaily.trade_date }}</el-tag>
      </div>
      <div class="stock-price-block">
        <span class="stock-price">{{ latestDaily?.close?.toFixed(2) ?? '-' }}</span>
        <span class="stock-price__unit">元</span>
      </div>
      <div class="stock-change" :class="latestDaily && latestDaily.change_pct > 0 ? 'up' : latestDaily && latestDaily.change_pct < 0 ? 'down' : 'flat'">
        <span>{{ latestDaily ? (latestDaily.change_pct > 0 ? '+' : '') + latestDaily.change_pct.toFixed(2) : '-' }}%</span>
        <span class="stock-change__amt">{{ latestDaily ? (latestDaily.change_pct > 0 ? '+' : '') + (latestDaily.change_amount ?? 0).toFixed(2) : '-' }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stock-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  background: white;
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  box-shadow: var(--shadow-md);
  border: 1px solid rgba(0, 0, 0, 0.04);
  margin-bottom: 12px;
}

.stock-name {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 6px;
  letter-spacing: -0.3px;
}

.stock-name-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stock-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.stock-meta__sep {
  color: #d1d5db;
}

.stock-header__right {
  text-align: right;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.stock-price-block {
  display: flex;
  align-items: baseline;
  justify-content: flex-end;
  gap: 4px;
}

.stock-price {
  font-size: 34px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -1px;
}

.stock-price__unit {
  font-size: 14px;
  color: var(--color-text-muted);
}

.stock-change {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 4px;
}

.stock-change.up .stock-change__amt,
.stock-change.up { color: var(--color-rise); }
.stock-change.down .stock-change__amt,
.stock-change.down { color: var(--color-fall); }
.stock-change.flat { color: var(--color-flat); }

.stock-change span:first-child {
  font-size: 16px;
  font-weight: 600;
}

.stock-change__amt {
  font-size: 13px;
}

.watchlist-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border-radius: 6px;
  font-size: 13px;
  padding: 6px 12px;
  margin-top: -3px;
}
</style>