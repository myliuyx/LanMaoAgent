import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/LoginPage.vue'),
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/pages/DashboardPage.vue'),
    meta: { title: '数据平台控制台' },
  },
  {
    path: '/wendgu',
    name: 'Wendgu',
    component: () => import('@/pages/WendguPage.vue'),
    meta: { title: '问股' },
  },
  {
    path: '/selection',
    name: 'Selection',
    component: () => import('@/pages/SelectionPage.vue'),
    meta: { title: '选股工作台' },
  },
  {
    path: '/watchlist',
    name: 'Watchlist',
    component: () => import('@/pages/WatchlistPage.vue'),
    meta: { title: '自选股' },
  },
  {
    path: '/stocks/:symbol',
    name: 'StockDetail',
    component: () => import('@/pages/StockDetailPage.vue'),
    meta: { title: '个股详情' },
  },
  {
    path: '/boards',
    name: 'BoardList',
    component: () => import('@/pages/BoardListPage.vue'),
    meta: { title: '板块分析' },
  },
  {
    path: '/boards/:boardCode',
    name: 'BoardDetail',
    component: () => import('@/pages/BoardDetailPage.vue'),
    meta: { title: '板块详情' },
  },
  {
    path: '/jobs',
    name: 'JobList',
    component: () => import('@/pages/JobListPage.vue'),
    meta: { title: '任务管理' },
  },
  {
    path: '/task-trigger',
    name: 'TaskTrigger',
    component: () => import('@/pages/TaskTriggerPage.vue'),
    meta: { title: '任务触发' },
  },
  {
    path: '/jobs/:jobId',
    name: 'JobDetail',
    component: () => import('@/pages/JobDetailPage.vue'),
    meta: { title: '任务详情' },
  },
  {
    path: '/coverage',
    name: 'Coverage',
    component: () => import('@/pages/CoveragePage.vue'),
    meta: { title: '数据覆盖' },
  },
  {
    path: '/backfill',
    name: 'Backfill',
    component: () => import('@/pages/BackfillPage.vue'),
    meta: { title: '补历史数据' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/pages/SettingsPage.vue'),
    meta: { title: '系统设置' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/pages/NotFoundPage.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：登录校验
router.beforeEach(async (to) => {
  const token = localStorage.getItem('token')
  // 白名单：登录页可直接访问
  if (to.path === '/login') {
    return true
  }
  // 其他页面需要登录态
  if (!token) {
    return '/login'
  }
  // tokenVerified 已在 login 时设为 true，跳过重复验证
  return true
})

export default router
