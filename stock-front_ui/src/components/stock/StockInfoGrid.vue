<script setup lang="ts">
import { ElIcon } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import type { StockProfile } from '@/types/stock'
import { formatDate } from '@/utils/format'

defineProps<{
  profile: StockProfile | null
  area: string | null
}>()
</script>

<template>
  <div class="page-card" style="margin: 16px 0">
    <div class="section-header">
      <el-icon><InfoFilled /></el-icon> 基本信息
    </div>
    <div class="info-grid">
      <div class="info-item"><span class="info-item__label">股票代码</span><span class="info-item__value">{{ profile?.symbol ?? '-' }}</span></div>
      <div class="info-item"><span class="info-item__label">交易所</span><span class="info-item__value">{{ profile?.exchange === 'SH' ? '上海证券交易所' : profile?.exchange === 'SZ' ? '深圳证券交易所' : profile?.exchange === 'BJ' ? '北京证券交易所' : profile?.exchange }}</span></div>
      <div class="info-item"><span class="info-item__label">上市状态</span>
        <el-tag :type="profile?.is_st ? 'danger' : 'success'" size="small" effect="plain">{{ profile?.is_st ? 'ST' : '正常' }}</el-tag>
      </div>
      <div class="info-item"><span class="info-item__label">一级行业</span><span class="info-item__value">{{ profile?.industry_l1 ?? '-' }}</span></div>
      <div class="info-item"><span class="info-item__label">二级行业</span><span class="info-item__value">{{ profile?.industry_l2 ?? '-' }}</span></div>
      <div class="info-item"><span class="info-item__label">地域</span><span class="info-item__value">{{ area ?? '-' }}</span></div>
      <div class="info-item"><span class="info-item__label">上市日期</span><span class="info-item__value">{{ formatDate(profile?.list_date ?? '') }}</span></div>
      <div class="info-item"><span class="info-item__label">上市板块</span><span class="info-item__value">{{ profile?.list_board ?? '-' }}</span></div>
    </div>
  </div>
</template>

<style scoped>
.page-card {
  background: white;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  padding: 14px 20px;
  border-bottom: 1px solid #f1f5f9;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  padding: 16px 20px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
}

.info-item__label {
  font-size: 12px;
  color: var(--color-text-muted);
  white-space: nowrap;
  min-width: 60px;
}

.info-item__value {
  font-size: 13px;
  color: var(--color-text-primary);
  font-weight: 500;
}
</style>