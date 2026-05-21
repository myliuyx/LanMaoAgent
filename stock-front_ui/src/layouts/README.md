# Layouts（布局组件）文档

> 本目录包含项目的布局组件。
> 目前只有一个主布局，所有页面都包裹在其中。

---

## MainLayout.vue - 主布局

### 组件结构

```
MainLayout.vue
├── el-container（外层容器）
│   ├── el-aside（左侧边栏，200px 宽）
│   │   ├── logo（顶部 Logo 区域）
│   │   └── el-menu（导航菜单）
│   │
│   └── el-container（右侧内容区）
│       ├── el-header（顶部栏）
│       │   ├── page-title（页面标题）
│       │   └── header-right（退出登录等）
│       │
│       └── el-main（主内容区）
│           └── <slot />（路由页面内容）
```

### 功能说明

#### 侧边栏菜单
- 固定宽度 200px
- 背景色：`#304156`（深蓝色）
- 菜单项高亮：当前路由对应的菜单项自动高亮

#### 菜单配置

```typescript
const menuItems = [
  { path: '/dashboard', label: '首页', icon: 'HomeFilled' },
  { path: '/selection', label: '选股工作台', icon: 'DataAnalysis' },
  { path: '/boards', label: '板块分析', icon: 'PieChart' },
  { path: '/jobs', label: '任务管理', icon: 'Clock' },
  { path: '/coverage', label: '数据覆盖', icon: 'Grid' },
  { path: '/backfill', label: '补历史', icon: 'Refresh' },
  { path: '/settings', label: '系统设置', icon: 'Setting' },
]
```

#### 交互说明
- 点击菜单项 → `router.push(path)` 跳转
- 退出登录按钮 → 调用 `useAppStore().logout()`，清除 token 并跳转登录页

### 样式变量

| 元素 | 背景色 |
|------|--------|
| 侧边栏 | `#304156` |
| Logo 区域 | `#3d4a5c` |
| 菜单激活项 | `#263445` |
| 主内容区 | `#f5f7fa`（浅灰） |

### 后续扩展方向
- 添加 Icon（当前只有文字标签，可引入 `@element-plus/icons-vue`）
- 菜单支持折叠（`isCollapse` 已预留）
- 顶部栏增加用户信息展示
- 面包屑导航
