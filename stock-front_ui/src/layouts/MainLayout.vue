<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { stockApi } from '@/api/stock'
import { boardApi } from '@/api/board'
import { jobApi } from '@/api/job'
import {
  HomeFilled,
  DataAnalysis,
  PieChart,
  Clock,
  Grid,
  Refresh,
  Setting,
  Search,
  ArrowDown,
  Histogram,
  Filter,
  Download,
  Star,
  TrendCharts,
} from '@element-plus/icons-vue'
import type { BoardItem } from '@/types/board'
import type { JobItem } from '@/types/job'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const isCollapse = ref(false)

// ── 全局搜索 ──────────────────────────────────────────
const searchQuery = ref('')
const searchResults = ref<{
  stocks: { symbol: string; name: string; exchange: string }[]
  boards: BoardItem[]
  jobs: JobItem[]
}>({ stocks: [], boards: [], jobs: [] })
const showDropdown = ref(false)
const searchInputRef = ref<HTMLInputElement | null>(null)
let searchTimer: ReturnType<typeof setTimeout> | null = null
let searchController: AbortController | null = null

type NavType = 'stock' | 'board' | 'job'
type NavHandler = (id: string | number) => ReturnType<typeof router.push>

const NAV_MAP: Record<NavType, NavHandler> = {
  stock: (id: string | number) => router.push(`/stocks/${String(id)}`),
  board: (id: string | number) => router.push(`/boards/${String(id)}`),
  job: (id: string | number) => router.push(`/jobs/${Number(id)}`),
}


async function doSearch(q: string) {
  // 取消上一个未完成的请求
  if (searchController) {
    searchController.abort()
  }
  searchController = new AbortController()
  if (!q.trim()) {
    searchResults.value = { stocks: [], boards: [], jobs: [] }
    return
  }
  const [stockRes, boardRes, jobRes] = await Promise.all([
    stockApi.search(q, 3, searchController.signal),
    boardApi.getList({ keyword: q, page_size: 3 }, searchController.signal),
    jobApi.getList({ job_name: q, page_size: 3, signal: searchController.signal }),
  ])
  searchResults.value = {
    stocks: stockRes.data ?? [],
    boards: boardRes.data?.list ?? [],
    jobs: jobRes.data?.list ?? [],
  }
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  if (!searchQuery.value.trim()) {
    searchResults.value = { stocks: [], boards: [], jobs: [] }
    showDropdown.value = false
    return
  }
  showDropdown.value = true
  searchTimer = setTimeout(() => doSearch(searchQuery.value), 280)
}

function onResultClick(type: NavType, id: string | number) {
  showDropdown.value = false
  searchQuery.value = ''
  void NAV_MAP[type](id)
}

function onSearchBlur() {
  window.setTimeout(() => { showDropdown.value = false }, 180)
}

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
  searchController?.abort()
})

function hasResults(): boolean {
  const r = searchResults.value
  return r.stocks.length > 0 || r.boards.length > 0 || r.jobs.length > 0
}

// ── 菜单 ─────────────────────────────────────────────
const menuItems = [
  { path: '/dashboard', label: '首页', icon: HomeFilled },
  { path: '/wendgu', label: '问股', icon: TrendCharts },
  { path: '/selection', label: '选股工作台', icon: DataAnalysis },
  { path: '/watchlist', label: '自选股', icon: Star },
  { path: '/boards', label: '板块分析', icon: PieChart },
  { path: '/jobs', label: '任务管理', icon: Clock },
  { path: '/task-trigger', label: '任务触发', icon: Refresh },
  { path: '/coverage', label: '数据覆盖', icon: Grid },
  { path: '/backfill', label: '补历史', icon: Refresh },
  { path: '/settings', label: '系统设置', icon: Setting },
]
</script>

<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside class="sidebar" :class="{ collapsed: isCollapse }">
      <!-- Logo -->
      <div class="sidebar-logo">
        <div class="sidebar-logo__icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z" rx="2" fill="currentColor" opacity="0.9"/>
            <path d="M6 6h1v1H6zM17 6h1v1h-1zM17 17h1v1h-1zM6 17h1v1H6z" rx="0.5" fill="white"/>
          </svg>
        </div>
        <transition name="fade">
          <span v-if="!isCollapse" class="sidebar-logo__text">A股数据平台</span>
        </transition>
      </div>

      <!-- 菜单 -->
      <el-menu
        :default-active="route.path"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        class="sidebar-menu"
        background-color="transparent"
        text-color="#94a3b8"
        active-text-color="#ffffff"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.path"
          :index="item.path"
          class="sidebar-menu__item"
        >
          <el-icon class="sidebar-menu__icon">
            <component :is="item.icon" />
          </el-icon>
          <template #title>
            <span class="sidebar-menu__label">{{ item.label }}</span>
          </template>
        </el-menu-item>
      </el-menu>

      <!-- 折叠按钮 -->
      <div class="sidebar-collapse" @click="isCollapse = !isCollapse">
        <el-icon :size="14">
          <ArrowDown :style="{ transform: isCollapse ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }" />
        </el-icon>
      </div>
    </el-aside>

    <!-- 右侧内容 -->
    <el-container class="main-container">
      <!-- 顶栏 -->
      <el-header class="topbar">
        <div class="topbar__left">
          <span class="topbar__title">{{ route.meta?.title || 'A股数据平台' }}</span>
        </div>
        <div class="topbar__right">
          <!-- 全局搜索 -->
          <div class="global-search">
            <el-input
              ref="searchInputRef"
              v-model="searchQuery"
              placeholder="搜索股票 / 板块 / 任务..."
              size="small"
              class="search-input"
              @input="onSearchInput"
              @focus="searchQuery && (showDropdown = true)"
              @blur="onSearchBlur"
            >
              <template #prefix>
                <el-icon class="search-icon"><Search /></el-icon>
              </template>
            </el-input>

            <!-- 搜索结果下拉 -->
            <transition name="dropdown">
              <div v-if="showDropdown && hasResults()" class="search-dropdown">
                <div v-if="searchResults.stocks.length" class="search-group">
                  <div class="search-group__title">
                    <el-icon size="12"><Histogram /></el-icon> 股票
                  </div>
                  <div
                    v-for="s in searchResults.stocks"
                    :key="s.symbol"
                    class="search-item"
                    @mousedown.prevent="onResultClick('stock', s.symbol)"
                  >
                    <span class="search-item__name">{{ s.name }}</span>
                    <span class="search-item__sub">{{ s.symbol }}</span>
                  </div>
                </div>
                <div v-if="searchResults.boards.length" class="search-group">
                  <div class="search-group__title">
                    <el-icon size="12"><PieChart /></el-icon> 板块
                  </div>
                  <div
                    v-for="b in searchResults.boards"
                    :key="b.board_code"
                    class="search-item"
                    @mousedown.prevent="onResultClick('board', b.board_code)"
                  >
                    <span class="search-item__name">{{ b.board_name }}</span>
                    <span class="search-item__sub">{{ b.board_code }}</span>
                  </div>
                </div>
                <div v-if="searchResults.jobs.length" class="search-group">
                  <div class="search-group__title">
                    <el-icon size="12"><Clock /></el-icon> 任务
                  </div>
                  <div
                    v-for="j in searchResults.jobs"
                    :key="j.id"
                    class="search-item"
                    @mousedown.prevent="onResultClick('job', j.id)"
                  >
                    <span class="search-item__name">{{ j.job_name }}</span>
                    <span class="search-item__sub">#{{ j.id }}</span>
                  </div>
                </div>
              </div>
            </transition>

            <!-- 无结果 -->
            <transition name="dropdown">
              <div
                v-if="showDropdown && searchQuery.trim() && !hasResults()"
                class="search-dropdown search-dropdown--empty"
              >
                <div class="search-empty">未找到相关结果</div>
              </div>
            </transition>
          </div>

          <el-dropdown trigger="click">
            <div class="user-avatar">
              <span>A</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item divided @click="appStore.logout()">
                  <el-icon><ArrowDown /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容区 -->
      <el-main class="main-content">
        <slot />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
/* ── 整体布局 ─────────────────────────────────────────────── */
.layout-container {
  height: 100%;
}

.main-container {
  flex-direction: column;
  background: var(--color-bg);
}

/* ── 侧边栏 ─────────────────────────────────────────────── */
.sidebar {
  width: 220px !important;
  background: var(--color-sidebar-bg);
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255, 255, 255, 0.04);
  transition: width var(--transition-base);
  overflow: hidden;
}

.sidebar.collapsed {
  width: 64px !important;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  min-height: 64px;
  overflow: hidden;
}

.sidebar-logo__icon {
  width: 34px;
  height: 34px;
  background: linear-gradient(135deg, #4f8fe8, #60a5fa);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(79, 143, 232, 0.4);
}

.sidebar-logo__text {
  font-size: 15px;
  font-weight: 700;
  color: white;
  white-space: nowrap;
  letter-spacing: -0.3px;
}

.sidebar-menu {
  flex: 1;
  border-right: none !important;
  padding: 8px 0;
}

.sidebar-menu__item {
  margin: 2px 8px !important;
  border-radius: 8px !important;
  height: 42px !important;
  transition: background var(--transition-fast) !important;
}

.sidebar-menu__item:hover {
  background: var(--color-sidebar-hover) !important;
}

.sidebar-menu__item.is-active {
  background: var(--color-sidebar-active) !important;
  color: white !important;
}

.sidebar-menu__item.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  background: #4f8fe8;
  border-radius: 0 2px 2px 0;
}

.sidebar-menu__icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  margin-right: 10px;
}

.sidebar-menu__label {
  font-size: 14px;
  font-weight: 500;
}

.sidebar-collapse {
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #475569;
  cursor: pointer;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  transition: color var(--transition-fast);
}

.sidebar-collapse:hover {
  color: #94a3b8;
}

/* ── 顶栏 ────────────────────────────────────────────────── */
.topbar {
  height: 60px !important;
  background: white;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px !important;
  box-shadow: var(--shadow-sm);
}

.topbar__left {
  display: flex;
  align-items: center;
}

.topbar__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.topbar__right {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* ── 全局搜索 ─────────────────────────────────────────────── */
.global-search {
  position: relative;
}

.search-input {
  width: 260px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid transparent;
  box-shadow: none !important;
  transition: all var(--transition-fast);
}

.search-input :deep(.el-input__wrapper:hover),
.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary);
  background: white;
}

.search-icon {
  color: var(--color-text-muted);
}

.search-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  width: 320px;
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  border: 1px solid #f1f5f9;
  z-index: 1000;
  overflow: hidden;
  padding: 6px 0;
}

.search-dropdown--empty {
  padding: 20px;
}

.search-group {
  padding: 4px 0;
}

.search-group + .search-group {
  border-top: 1px solid #f1f5f9;
}

.search-group__title {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--color-text-muted);
  padding: 4px 14px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}

.search-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  cursor: pointer;
  transition: background var(--transition-fast);
  border-radius: 4px;
  margin: 0 4px;
}

.search-item:hover {
  background: #f8fafc;
}

.search-item__name {
  font-size: 13px;
  color: var(--color-text-primary);
  font-weight: 500;
}

.search-item__sub {
  font-size: 11px;
  color: var(--color-text-muted);
}

.search-empty {
  text-align: center;
  color: var(--color-text-muted);
  font-size: 13px;
  padding: 8px 0;
}

/* ── 用户头像 ─────────────────────────────────────────────── */
.user-avatar {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #4f8fe8, #60a5fa);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: box-shadow var(--transition-fast);
}

.user-avatar:hover {
  box-shadow: 0 2px 8px rgba(79, 143, 232, 0.4);
}

/* ── 主内容区 ─────────────────────────────────────────────── */
.main-content {
  padding: 0;
  overflow-y: auto;
  background: var(--color-bg);
}

/* ── 过渡动画 ─────────────────────────────────────────────── */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
