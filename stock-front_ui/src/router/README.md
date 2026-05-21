# Router（路由配置）文档

> 本目录包含 Vue Router 的配置。
> 当前仅有一个文件：`index.ts`

---

## index.ts - 路由配置

### 路由列表

```typescript
const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', name: 'Login', component: () => import('@/pages/LoginPage.vue') },
  { path: '/dashboard', name: 'Dashboard', component: () => import('@/pages/DashboardPage.vue') },
  { path: '/selection', name: 'Selection', component: () => import('@/pages/SelectionPage.vue') },
  { path: '/stocks/:symbol', name: 'StockDetail', component: () => import('@/pages/StockDetailPage.vue') },
  { path: '/boards', name: 'BoardList', component: () => import('@/pages/BoardListPage.vue') },
  { path: '/boards/:boardCode', name: 'BoardDetail', component: () => import('@/pages/BoardDetailPage.vue') },
  { path: '/jobs', name: 'JobList', component: () => import('@/pages/JobListPage.vue') },
  { path: '/jobs/:jobId', name: 'JobDetail', component: () => import('@/pages/JobDetailPage.vue') },
  { path: '/coverage', name: 'Coverage', component: () => import('@/pages/CoveragePage.vue') },
  { path: '/backfill', name: 'Backfill', component: () => import('@/pages/BackfillPage.vue') },
  { path: '/settings', name: 'Settings', component: () => import('@/pages/SettingsPage.vue') },
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/pages/NotFoundPage.vue') },
]
```

### 配置说明

- **路由模式**：`history` 模式（URL 不带 `#`）
- **懒加载**：所有页面组件使用动态导入（`() => import(...)`）
- **默认跳转**：`/` → `/dashboard`
- **404 处理**：匹配 `/:pathMatch(.*)*` 跳转到 `NotFoundPage.vue`

### 路由元信息（meta）

当前未使用 `meta` 字段，后续可扩展：
```typescript
{
  path: '/dashboard',
  name: 'Dashboard',
  component: () => import('@/pages/DashboardPage.vue'),
  meta: { title: '首页', requiresAuth: true }
}
```

### 路由守卫

```typescript
// 路由守卫：登录校验
router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  // 白名单：登录页可直接访问
  if (to.path === '/login') {
    return true
  }
  // 其他页面需要登录态
  if (!token) {
    return '/login'
  }
  return true
})
```

**规则：**
- `/login` 无限制访问
- 其他所有路由：未登录 → 强制跳转 `/login`
- 401 响应 → 响应拦截器处理（见 `request.ts`）

### 注意事项

- **路由守卫**：已实现 `beforeEach` 守卫，未登录强制跳转 `/login`
- **Token 过期**：由 `request.ts` 响应拦截器处理 401 跳转登录
- **`MainLayout` 包裹**：`App.vue` 中 `MainLayout` 包裹 `<RouterView />`，所有页面都在主布局内渲染
- **动态参数**：
  - `/stocks/:symbol` — `symbol` 格式如 `600519.SH`
  - `/boards/:boardCode` — 板块代码
  - `/jobs/:jobId` — 任务 ID（数字）

### 获取路由参数

```typescript
// 在组件中获取路由参数
import { useRoute } from 'vue-router'

const route = useRoute()
const symbol = route.params.symbol  // '600519.SH'
const jobId = route.params.jobId   // '123'
```
