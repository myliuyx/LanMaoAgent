# Stores（Pinia 状态管理）文档

> 本目录包含 Pinia 全局状态管理。
> 每个 Store 负责一个业务域的状态存储和业务逻辑。

---

## 文件索引

| 文件 | 用途 |
|------|------|
| `app.ts` | 全局状态（token、用户信息、登录状态） |
| `tradeDate.ts` | 交易日状态（当前交易日、是否交易日） |
| `job.ts` | 任务状态（运行中任务列表、轮询控制） |
| `selectionTemplate.ts` | 选股模板管理 |

---

## app.ts - 全局状态

### State
```typescript
token: string                     // JWT token（从 localStorage 恢复）
isLoggedIn: boolean              // 是否已登录
userInfo: { id, username, role } // 用户信息
```

### Actions
```typescript
setToken(token: string): void
  // 设置 token，写入 localStorage

setUserInfo(info: { id, username, role }): void
  // 设置用户信息

logout(): void
  // 清除 token、userInfo、localStorage，router.push('/login') 跳转登录页
```

### 使用示例
```typescript
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
if (appStore.isLoggedIn) {
  // 已登录
}
```

---

## tradeDate.ts - 交易日状态

### State
```typescript
currentTradeDate: string   // 当前系统交易日（YYYY-MM-DD）
isTradeDay: boolean        // 今天是否交易日
```

### Actions
```typescript
setTradeDate(date: string, isTrade: boolean): void
  // 设置当前交易日和是否交易日
```

---

## job.ts - 任务状态

### State
```typescript
runningJobs: JobItem[]       // 运行中的任务（Dashboard 和 JobManage 共享）
latestJobs: JobItem[]        // 最新任务列表
pollTimer: number | null     // 轮询定时器 ID
```

### Actions
```typescript
fetchRunningJobs(): Promise<void>
  // 调用 GET /api/v1/jobs?status=RUNNING
  // 更新 runningJobs

startPolling(intervalMs?: number): void
  // 启动轮询，默认间隔 10 秒
  // 立即执行一次 fetchRunningJobs

stopPolling(): void
  // 停止轮询，清除定时器
```

### 轮询策略
- Dashboard 页面 `onMounted` 时调用 `startPolling()`
- Dashboard 页面 `onUnmounted` 时调用 `stopPolling()`
- 后续可升级为 WebSocket

---

## selectionTemplate.ts - 选股模板

### 类型
```typescript
interface SelectionTemplate {
  id: number
  name: string
  filters: Record<string, unknown>   // 筛选条件
  createdAt: string
}
```

### State
```typescript
templates: SelectionTemplate[]   // 保存的模板列表
```

### Actions
```typescript
addTemplate(template: SelectionTemplate): void
  // 添加模板到列表

removeTemplate(id: number): void
  // 从列表移除指定模板
```

### 注意事项
- 当前仅内存存储，未持久化到后端
- 后续需要调用后端接口保存到数据库
