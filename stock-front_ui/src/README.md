# src/ 目录文档

> 本目录是前端项目的源代码根目录，所有业务代码都在这里。

---

## 目录索引

| 目录/文件 | 说明 | 详情 |
|-----------|------|------|
| `main.ts` | 应用入口文件 | 挂载 Vue 应用、注册插件 |
| `App.vue` | 根组件 | 包裹 MainLayout 和 RouterView |
| `api/` | API 请求层 | 统一封装所有后端接口 |
| `assets/` | 静态资源 | CSS、图片等 |
| `components/` | Vue 组件 | 基础组件 + 业务组件 |
| `layouts/` | 布局组件 | 主布局 MainLayout |
| `pages/` | 路由页面 | 12 个页面组件 |
| `router/` | 路由配置 | Vue Router 配置 |
| `stores/` | 状态管理 | Pinia Store |
| `types/` | 类型定义 | TypeScript 类型 |
| `utils/` | 工具函数 | 格式化、常量 |

---

## main.ts - 应用入口

```typescript
// 1. 创建 Vue 应用
const app = createApp(App)

// 2. 注册插件
app.use(createPinia())        // Pinia 状态管理
app.use(router)               // Vue Router
app.use(ElementPlus, {        // Element Plus UI 组件库
  locale: zhCn                // 中文语言包
})

// 3. 挂载到 #app
app.mount('#app')
```

---

## App.vue - 根组件

```vue
<template>
  <MainLayout>
    <RouterView />
  </MainLayout>
</template>
```

- `MainLayout` — 左侧边栏 + 顶部栏 + 内容区的整体布局
- `RouterView` — 当前路由页面，在布局的内容区渲染

---

## 组件层级

```
App.vue
└── MainLayout.vue
    └── RouterView
        ├── DashboardPage.vue
        ├── SelectionPage.vue
        ├── StockDetailPage.vue
        ├── BoardListPage.vue
        ├── BoardDetailPage.vue
        ├── JobListPage.vue
        ├── JobDetailPage.vue
        ├── CoveragePage.vue
        ├── BackfillPage.vue
        ├── SettingsPage.vue
        ├── LoginPage.vue
        └── NotFoundPage.vue
```

---

## 数据流向

```
用户操作
    ↓
页面组件（如 SelectionPage.vue）
    ↓ 调用
API 层（如 selectionApi.query()）
    ↓ 发送 HTTP 请求
后端 FastAPI（localhost:8000/api/v1/...）
    ↓ 返回 JSON
API 层解析 response.data
    ↓
页面组件更新视图 或 Store 更新状态
```

---

## 状态管理数据流

```
Store（如 useJobStore）
    ├── State: runningJobs, latestJobs
    ├── Actions: fetchRunningJobs(), startPolling(), stopPolling()
    ↓
页面组件（如 DashboardPage.vue）
    ├── onMounted → startPolling() 启动轮询
    └── 模板中使用 {{ jobStore.runningJobs }}
```
