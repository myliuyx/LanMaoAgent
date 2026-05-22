# 高优先级问题修复方案

## 目标

修复5个高优先级问题：1个安全漏洞（maxBuffer过小）、1个Bug（循环检测失效）、1个安全绕过（catch分支）、1个代码质量问题（重复构建headers）、1个质量改进（缺少retryable）。

---

## 现状分析

### 问题1: TerminalHandler maxBuffer 过小
- **文件**: `packages/tools/terminal/src/TerminalHandler.ts`
- **位置**: 第145行附近，`execFile` 的 options 中 `maxBuffer: 20 * 1024` (20KB)
- **影响**: 命令输出超过20KB时会被截断并抛出 `maxBuffer exceeded` 错误，导致工具调用失败

### 问题2: AgentConfig extends 循环检测失效
- **文件**: `apps/cli/src/index.ts`
- **位置**: 第85行 `for (const id of index)` 中每次调用 `resolveOne(id, new Set())`
- **影响**: 每个顶层 agent 的 visited Set 是独立的，兄弟节点间的循环检测完全失效。例如 A extends B, B extends A 时，从A开始不会检测到B对A的引用（因为visited是空的），而从B开始也不会检测到A对B的引用

### 问题3: safeResolve catch 分支绕过安全检查
- **文件**: `packages/tools/filesystem/src/pathUtils.ts`
- **位置**: 第45行 `catch { return resolved }`
- **影响**: 当 realpathSync 抛出异常时（如权限不足、符号链接循环等），直接返回原始解析路径，绕过了安全校验。攻击者可能利用此绕过 allowlist

### 问题4: OpenAIAdapter 重复构建 headers
- **文件**: `packages/llm-adapter/src/OpenAIAdapter.ts`
- **位置**: 
  - `buildRequest()` 方法内部构建了 headers（第108-112行）但仅用于局部变量，未返回
  - `completeOnce()` 中又重复构建相同的 headers（第135-138行）
- **影响**: 代码重复、不一致风险（如未来修改 header 逻辑需改两处）

### 问题5: GitHandler 错误缺少 retryable
- **文件**: `packages/tools/git/src/GitHandler.ts`
- **位置**: 第80行 catch 块返回 `{ content: safeErrorMessage(e), isError: true }`
- **影响**: 所有 git 错误（包括网络超时、临时失败）都被标记为不可重试，导致 agent 无法自动恢复

---

## 实现步骤

### 任务1: TerminalHandler maxBuffer 修复

**文件**: `packages/tools/terminal/src/TerminalHandler.ts`

**修改位置**: 第145行附近

```typescript
// 原代码 (约第143-147行):
execFile(
  name,
  cmdArgs,
  {
    cwd: ctx.cwd,
    timeout: 30000,
    maxBuffer: 20 * 1024,
  },

// 修改为:
execFile(
  name,
  cmdArgs,
  {
    cwd: ctx.cwd,
    timeout: 30000,
    maxBuffer: 1 * 1024 * 1024, // 1MB — 修复：原20KB过小，导致大输出截断
  },
```

---

### 任务2: AgentConfig extends 循环检测修复

**文件**: `apps/cli/src/index.ts`

**修改位置**: `loadAgents` 函数内部

```typescript
// 原代码 (约第83-86行):
for (const id of index) {
    result.push(resolveOne(id, new Set()))
}

// 修改为:
const visited = new Set<string>() // 修复：共享 visited Set，使兄弟节点间也能检测循环
for (const id of index) {
    result.push(resolveOne(id, visited))
}
```

**注意**: `resolveOne` 函数内部的 `visited.add(id)` 和 `visited.has(id)` 逻辑保持不变。由于每个 agent 在成功加载后会被缓存到 `loaded` Map 中，即使共享 visited Set，也不会导致误判——因为已加载的 agent 会直接从缓存返回（第58行 `const cached = loaded.get(id)`）。

---

### 任务3: safeResolve catch 分支修复

**文件**: `packages/tools/filesystem/src/pathUtils.ts`

**修改位置**: 第45行

```typescript
// 原代码 (约第44-46行):
} catch {
    return resolved
}

// 修改为:
} catch {
    // 修复：catch 分支不应返回原始路径，应抛出错误以阻止不安全访问
    throw new Error(`Failed to resolve path safely: ${targetPath}`)
}
```

**影响分析**: `isInAllowedPath` 和 `validateAncestors` 都调用了 `safeResolve`。修改后，当 realpathSync 失败时会向上抛出错误，调用方需要处理。检查调用链：
- `isInAllowedPath`: 在循环中调用 `safeResolve(resolve(p))`，如果抛出异常会中断循环并传播——这是期望行为（安全优先）
- `validateAncestors`: 直接调用，同样会传播异常

---

### 任务4: OpenAIAdapter headers 去重

**文件**: `packages/llm-adapter/src/OpenAIAdapter.ts`

**修改位置1**: 在类中添加私有方法 `_buildHeaders()`（约在第105行 `private buildRequest` 之前）

```typescript
// 新增私有方法 (插入到 buildRequest 之前):
private _buildHeaders(): Record<string, string> {
    const headers: Record<string, string> = {}
    if (this.apiKey) {
        headers['authorization'] = `Bearer ${this.apiKey}`
    }
    return headers
}
```

**修改位置2**: 在 `completeOnce` 中复用 `_buildHeaders()`（约第135-138行）

```typescript
// 原代码 (约第134-139行):
const body = this.buildRequest(messages, tools)

const headers: Record<string, string> = {}
if (this.apiKey) {
    headers['authorization'] = `Bearer ${this.apiKey}`
}

// 修改为:
const body = this.buildRequest(messages, tools)
const headers = this._buildHeaders() // 修复：复用私有方法，避免重复构建
```

**注意**: `buildRequest` 内部也构建了 headers（第108-112行），但该方法并未返回 headers。如果未来需要，可以将 `_buildHeaders()` 的返回值从 `buildRequest` 中一并返回，或保持当前设计——`buildRequest` 只负责构建 body，headers 由 `_buildHeaders` 统一管理。

---

### 任务5: GitHandler retryable 修复

**文件**: `packages/tools/git/src/GitHandler.ts`

**修改位置**: 第80行 catch 块

```typescript
// 原代码 (约第79-81行):
} catch (e) {
    return { content: safeErrorMessage(e), isError: true }
}

// 修改为:
} catch (e) {
    // 修复：git 错误应标记为可重试，允许 agent 自动恢复（如网络超时、临时失败）
    return { content: safeErrorMessage(e), isError: true, retryable: true }
}
```

---

## 涉及文件列表

| # | 文件路径 | 修改类型 | 影响范围 |
|---|---------|---------|---------|
| 1 | `packages/tools/terminal/src/TerminalHandler.ts` | 单行修改 | maxBuffer 常量值 |
| 2 | `apps/cli/src/index.ts` | 3行修改（新增+替换） | loadAgents 函数中的循环逻辑 |
| 3 | `packages/tools/filesystem/src/pathUtils.ts` | 1行修改（return → throw） | safeResolve catch 分支 |
| 4 | `packages/llm-adapter/src/OpenAIAdapter.ts` | 新增方法+1处调用替换 | headers 构建逻辑去重 |
| 5 | `packages/tools/git/src/GitHandler.ts` | 单行修改（添加 retryable） | GitHandler execute catch 块 |

---

## 注意事项/风险

### 任务1 (maxBuffer)
- **低风险**: 仅增大缓冲区，不影响逻辑。但需注意内存使用——如果命令输出极大（接近1MB），会占用更多内存。这是可接受的权衡。

### 任务2 (visited Set)
- **中风险**: 共享 visited Set 后，如果一个 agent 加载失败（抛出异常），其 id 可能已被添加到 visited 中。但由于 `resolveOne` 在递归调用前才 `add(id)`，且失败时不会缓存到 loaded Map，下次从其他路径访问时会重新尝试——这是正确行为。
- **验证**: 确保测试覆盖 A→B→A 的循环场景。

### 任务3 (safeResolve throw)
- **中风险**: 将 return resolved 改为 throw Error 会改变 API 契约。调用方 `isInAllowedPath` 和 `validateAncestors` 目前未捕获异常，异常会向上传播到文件操作工具（如 read_file, write_file）。这是**期望行为**——安全优先于静默失败。
- **建议**: 在调用 safeResolve 的工具层（如 FileHandler）中，catch 该错误并返回适当的错误信息给用户。

### 任务4 (headers 去重)
- **低风险**: 纯重构，不改变功能行为。确保 `_buildHeaders()` 的逻辑与原来完全一致。

### 任务5 (retryable)
- **低风险**: 添加 `retryable: true` 使 git 错误可重试。如果 agent 频繁遇到 git 错误（如仓库损坏），可能导致无限重试循环——但现有 retry 机制应有上限保护。

---

## 测试建议

1. **TerminalHandler**: 测试输出超过20KB但不超过1MB的命令，确认不再截断
2. **AgentConfig**: 创建 A→B→A 的 agent.json 配置，确认抛出循环检测错误
3. **safeResolve**: 构造一个导致 realpathSync 失败的路径（如权限不足），确认抛出异常而非返回不安全路径
4. **OpenAIAdapter**: 验证 API 调用仍然正常工作，headers 正确设置
5. **GitHandler**: 模拟 git 命令超时或临时失败，确认 retryable 为 true
