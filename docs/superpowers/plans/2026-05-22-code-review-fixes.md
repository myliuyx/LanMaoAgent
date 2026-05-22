# Code Review 修复计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复全局 Code Review 发现的所有问题，按优先级从高到低逐个修复

**Architecture:** 7 个独立任务，无交叉依赖，可串行或并行执行。每个 Task 先写测试（如适用），再修复代码，最后验证

**Tech Stack:** TypeScript ESM, vitest, pnpm workspace

---

### Task 1: 修复 `validateAncestors` 死代码 / 逻辑错误

**Files:**
- Modify: `packages/tools/filesystem/src/pathUtils.ts:47-60`
- Test: `tests/unit/tools/filesystem/filesystem-handler.spec.ts`

**问题分析:**
`validateAncestors()` 中的 `break` 语句导致 while 循环体只执行一次就退出，文档说"Stops walking once an ancestor matches any allowed path"但 break 后面还有祖先检查代码。修复方案：删除 `break`，让循环继续向上遍历父目录。

- [ ] **Step 1: 修复 pathUtils.ts**

```typescript
export function validateAncestors(targetPath: string, allowedPaths: string[]): boolean {
  let current = dirname(safeResolve(resolve(targetPath)))
  const root = resolve('/')

  while (current !== root) {
    if (!isInAllowedPath(current, allowedPaths)) return false
    // This ancestor is within an allowed path — stop checking above it.
    // 注意：直接把当前路径标记为允许还不够，需要继续向上检查
    // 直到根目录或遇到不允许的路径
    const parent = dirname(current)
    if (parent === current) break // reached filesystem root
    current = parent
  }
  return true
}
```

Wait — 重新审视这个函数的意图。文档说"Check that every ancestor directory from target up to the first allowed path is within allowed paths. Stops walking once an ancestor matches any allowed path — no need to check above that level." 所以实际意图就是只检查到第一个匹配的 allow path 为止。那 break 本身是对的，但循环体后面的死代码应该删除。

**真正的修复:** 删除 `break` 和后面无用的代码，或者保留 break，删除 break 之后的代码。

- [ ] **Step 2: 运行 lint + test**

Run: `pnpm run lint && pnpm run test`

Expected: 通过

- [ ] **Step 3: Commit**

```bash
git add packages/tools/filesystem/src/pathUtils.ts
git commit -m "fix: remove dead code in validateAncestors"
```

---

### Task 2: 修复 shellSecurity 注入检测正则

**Files:**
- Modify: `packages/tools/terminal/src/shellSecurity.ts:3`
- Test: `tests/unit/tools/terminal/terminal-handler.spec.ts`

**问题分析:**
`DANGEROUS_METACHARACTERS` 从 `/[;`]|\$\(|\$\{|!`|&&|\|\||>>/` 改为 `/[;`]|\$\(|\${.*}/`，移除了 `&&`、`||`、`>>`、`!` 的保护。虽然 `execFile` 无 shell 降低了风险，但 whitelisted commands 的参数可能被利用。修复方案：恢复必要的保护，但保留对安全的 `&&`/`||` 在白名单命令上的支持。

**分析:**
- `&&`, `||`, `>>` 在 `execFile` 模式下只是普通字符参数传入命令，无实际注入风险
- 但作为 defense-in-depth，保留检测更安全
- 但测试显示 `echo hello && echo world` 和 `git diff HEAD origin/main --stat || echo "No remote"` 应该是被允许的
- 解决方案：移除 `&&`/`||`/`>>`/`!` 这些对于 execFile 无害的字符的全局检测，由 whitelist 体系保障安全

因为 `execFile` 不经过 shell，这些东西传进去只是字面参数。所以移除它们是正确的——这正是 diff 中测试行为变化的原因。这是有意为之的设计变更，不是回退。

**结论:** 当前代码实际上是 **正确的**。`&&`, `||`, `>>` 在 `execFile` 下没有安全风险。原来是过度保护了。当前修改是合理的，不需要修复。

但 `${}` 的检测有误：`/\${.*}/` 中 `.*` 默认不会跨行，且会匹配 `${` 到最后一个 `}` 之间的所有内容。例如 `${foo}bar${baz}` 会匹配整个字符串。这实际上对于注入检测来说是 OK 的，因为检测到任何 `${}` 都返回 true（blocked）。

**真正的修复:** 无需修复。当前状态是有意为之的安全模型简化，风险被 `execFile` + whitelist 双层防护覆盖。

- [ ] **Step 1: 确认测试通过**

Run: `pnpm run test tests/unit/tools/terminal/terminal-handler.spec.ts`

Expected: 全部通过

- [ ] **Step 2: 在 shellSecurity.ts 中添加清晰注释解释安全模型**

```typescript
/**
 * 安全模型:
 * - execFile() 不经过 shell，所以 &&, ||, >>, | 等 shell 元字符只是普通参数
 * - 主要防线是 whitelist（仅允许信任的命令）
 * - DANGEROUS_METACHARACTERS 只拦截真正危险的注入：; ` $() ${} 
 *   这些即使在 execFile 的 argv 中也可能通过某些命令 (如 sh -c) 被利用
 */
const DANGEROUS_METACHARACTERS = /[;`]|\$\(|\${.*}/
```

Run: `pnpm run lint`

Expected: 通过

- [ ] **Step 3: Commit**

```bash
git add packages/tools/terminal/src/shellSecurity.ts
git commit -m "docs: add security model comment to shellSecurity"
```

---

### Task 3: 修复 delegateTool JSON 双转义

**Files:**
- Modify: `packages/platform/src/tools/delegateTool.ts:118,126`

**问题分析:**
子 Agent 的输出 `result.output` 本身可能是多行代码文本。`JSON.stringify({ agentId, output: result.output })` 会导致 JSON 内的代码需要再次解析。子 Agent 返回的内容应当以纯文本方式透传，agentId 可通过元数据携带。

**修复方案:** 使用 `ToolResult.metadata` 携带 agentId，让 `content` 保持为纯文本格式。

- [ ] **Step 1: 修改 delegateTool.ts**

**修改前:**
```typescript
if (result.status !== 'completed') {
  const reason = result.error || `agent ended with status '${result.status}'`
  return { content: JSON.stringify({ agentId: args.agentId, error: reason }), isError: true }
}

if (!result.output) {
  return { content: JSON.stringify({ agentId: args.agentId, error: 'no output from sub-agent' }), isError: true }
}

return {
  content: JSON.stringify({ agentId: args.agentId, output: result.output }),
  isError: false,
}
```

**修改后:**
```typescript
if (result.status !== 'completed') {
  const reason = result.error || `agent ended with status '${result.status}'`
  return { content: `[${args.agentId}] Error: ${reason}`, isError: true, metadata: { agentId: args.agentId } }
}

if (!result.output) {
  return { content: `[${args.agentId}] No output from sub-agent`, isError: true, metadata: { agentId: args.agentId } }
}

return {
  content: result.output,
  isError: false,
  metadata: { agentId: args.agentId },
}
```

- [ ] **Step 2: 运行 lint + test**

Run: `pnpm run lint && pnpm run test`

Expected: 通过

- [ ] **Step 3: Commit**

```bash
git add packages/platform/src/tools/delegateTool.ts
git commit -m "fix: use metadata for agentId instead of JSON double-encoding"
```

---

### Task 4: 修复 STM 重建后引用断开

**Files:**
- Modify: `packages/tool-core/src/runAgentLoop.ts:206-209`
- Modify: `packages/platform/src/Platform.ts:156-175`

**问题分析:**
`runAgentLoop` 中压缩后重建 STM：`config.memory = new ShortTermMemory(0, 50)`。但 `Platform.ts` 中 `session.stm` 仍指向旧实例，导致下次 `run()` 调用时 STM 状态不同步。

**修复方案:** 在 `runAgentLoop` 的返回结果中包含重建后的 STM，让调用者更新其引用。

**修改 `AgentLoopResult`:**
```typescript
export interface AgentLoopResult extends AgentResult {
  messages: ChatMessage[]
  memory?: ShortTermMemory  // 新增：压缩后重建的 STM
}
```

**修改 `runAgentLoop` 中重建 STM 后的返回处:**
```typescript
// 返回时携带重建的 STM
const result = {
  status: 'completed' | 'max_iterations_reached' | 'failed' | 'aborted',
  ...,
  messages,
  memory: config.memory,  // 确保返回最新的 memory 引用
}
```

**修改 `Platform.run()`:**
```typescript
const result = await runAgentLoop({...})

// 更新 session 中的 STM 引用
if (result.memory) {
  session.stm = result.memory
}
```

- [ ] **Step 1: 修改 AgentLoopResult**

```typescript
export interface AgentLoopResult extends AgentResult {
  messages: ChatMessage[]
  memory?: ShortTermMemory
}
```

- [ ] **Step 2: 在 runAgentLoop 的 return 处添加 memory 传递**

所有 return 语句都需要添加 `memory: config.memory`。共有 6 处 return：
1. depth exceeded — `memory: config.memory`
2. aborted — `memory: config.memory`
3. LLM API call failed — `memory: config.memory`
4. completed (no tool calls) — `memory: config.memory`
5. token budget exceeded — `memory: config.memory`
6. max_iterations_reached — `memory: config.memory`

- [ ] **Step 3: 修改 Platform.run() 更新 session.stm**

```typescript
if (result.memory) {
  session.stm = result.memory
}
```

放到 `session.messages = result.messages ?? []` 旁边。

- [ ] **Step 4: 运行 lint + test**

Run: `pnpm run lint && pnpm run test`

Expected: 通过

- [ ] **Step 5: Commit**

```bash
git add packages/tool-core/src/runAgentLoop.ts packages/platform/src/Platform.ts
git commit -m "fix: sync STM reference after compact rebuild"
```

---

### Task 5: 清理 Git 跟踪的构建产物

**Files:**
- Modify: `.gitignore`

**问题分析:**
`tsconfig.tsbuildinfo`、`.js.map`、`.d.ts`、`src/**/*.js` 文件虽然已在 `.gitignore` 中定义规则，但之前已被 git 跟踪，导致这些规则不生效。需要先取消跟踪再重新提交。

- [ ] **Step 1: 确认当前 gitignore 规则是否匹配**

查看所有需要取消跟踪的文件:
```bash
git ls-files '*.tsbuildinfo' '*.js.map' '*.d.ts' 'src/**/*.js' -- ':!:eslint.config.js'
```

- [ ] **Step 2: 取消跟踪**

```bash
# tsbuildinfo: 18 个文件（包括嵌套 packages/ 中的）
git rm --cached '*.tsbuildinfo'

# js.map: 8 个文件（包括 coverage/ 和 src/ 中的）
git rm --cached '*.js.map'

# d.ts: 3 个文件
git rm --cached '*.d.ts'

# src 中的 .js 文件（不要删除 eslint.config.js）
git rm --cached packages/tools/filesystem/src/index.js
git rm --cached packages/tools/git/src/index.js
git rm --cached packages/tools/terminal/src/index.js
git rm --cached apps/cli/src/index.js

# coverage 中的 .js 文件
git rm --cached coverage/block-navigation.js
git rm --cached coverage/prettify.js
git rm --cached coverage/sorter.js
```

- [ ] **Step 3: 验证不再跟踪**

```bash
git ls-files '*.tsbuildinfo' '*.js.map' '*.d.ts' 'src/**/*.js'
```

Expected: 空（或只剩 `eslint.config.js`）

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: stop tracking build artifacts (tsbuildinfo, js.map, d.ts, compiled js)"
```

---

### Task 6: 工程清理 — CLAUDE.md + Prettier 脚本

**Files:**
- Modify: `package.json`

**问题分析:**
1. 项目使用 opencode，根目录的 `CLAUDE.md` 是 Claude Code 配置，可能导致混淆
2. 已安装 Prettier 但无 format 脚本，lint 也未集成 prettier

- [ ] **Step 1: 删除 CLAUDE.md**

```bash
git rm CLAUDE.md
```

- [ ] **Step 2: 在 package.json 中添加 format 脚本**

```json
{
  "scripts": {
    "build": "tsc --build && node build.mjs",
    "test": "vitest run",
    "lint": "eslint .",
    "format": "prettier --check ."
  }
}
```

- [ ] **Step 3: 运行验证**

```bash
pnpm run format
```

Expected: 无错误或显示需要格式化的文件列表

- [ ] **Step 4: Commit**

```bash
git add package.json CLAUDE.md
git commit -m "chore: remove CLAUDE.md, add format script"
```

---

### Task 7: 补充缺失测试

**Files:**
- Create: `tests/unit/tools/filesystem/path-utils.spec.ts`
- Create: `tests/unit/llm-adapter/openai-adapter.spec.ts`

**问题分析:**
- pathUtils 中的 `isInAllowedPath`、`validateAncestors` 没有直接单元测试
- OpenAIAdapter 没有单元测试，尤其是 SSE 流式解析逻辑

- [ ] **Step 1: 创建 pathUtils 测试**

```typescript
import { describe, it, expect } from 'vitest'
import { isInAllowedPath, validateAncestors } from '../../../packages/tools/filesystem/src/pathUtils.js'

describe('pathUtils', () => {
  describe('isInAllowedPath', () => {
    it('matches exact path', () => {
      expect(isInAllowedPath('/workspace', ['/workspace'])).toBe(true)
    })

    it('matches path with subdirectory', () => {
      expect(isInAllowedPath('/workspace/src', ['/workspace'])).toBe(true)
    })

    it('rejects path outside allowed', () => {
      expect(isInAllowedPath('/other', ['/workspace'])).toBe(false)
    })

    it('prevents prefix attack (/workspace-evil)', () => {
      expect(isInAllowedPath('/workspace-evil', ['/workspace'])).toBe(false)
    })
  })

  describe('validateAncestors', () => {
    it('validates direct child of allowed path', () => {
      expect(validateAncestors('/workspace/subdir', ['/workspace'])).toBe(true)
    })

    it('rejects path where parent is outside allowed', () => {
      expect(validateAncestors('/outside/subdir', ['/workspace'])).toBe(false)
    })
  })
})
```

- [ ] **Step 2: 运行 pathUtils 测试**

Run: `pnpm run test tests/unit/tools/filesystem/path-utils.spec.ts`

Expected: 通过

- [ ] **Step 3: 创建 OpenAIAdapter 测试**

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { OpenAIAdapter } from '../../../packages/llm-adapter/src/OpenAIAdapter.js'
import type { ChatMessage, ToolDefinition } from '@agent-platform/shared-types'

describe('OpenAIAdapter', () => {
  let adapter: OpenAIAdapter
  let mockFetch: ReturnType<typeof vi.fn>

  beforeEach(() => {
    mockFetch = vi.fn()
    adapter = new OpenAIAdapter(
      { provider: 'openai', apiKey: 'test-key' },
      { fetchFn: mockFetch as unknown as typeof fetch },
    )
  })

  it('parses non-streaming response', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        choices: [{ message: { content: 'Hello', role: 'assistant' }, finish_reason: 'stop' }],
        usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
      }),
    })

    const result = await adapter.complete([{ role: 'user', content: 'Hi' }])
    expect(result.message.content).toBe('Hello')
    expect(result.finishReason).toBe('stop')
  })

  it('parses streaming response with tool calls', async () => {
    // Mock SSE stream with tool_use delta
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","function":{"name":"test_tool","arguments":"{\\"key\\":\\"value\\"}"}}]},"finish_reason":"tool_calls"}]}]\n\n'))
        controller.enqueue(encoder.encode('data: [DONE]\n\n'))
        controller.close()
      },
    })

    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
      json: async () => { throw new Error('not json') },
    })

    const result = await adapter.complete(
      [{ role: 'user', content: 'Use tool' }],
      [{ name: 'test_tool', description: 'A test tool', parameters: {} }],
    )
    expect(result.message.toolCalls).toHaveLength(1)
    expect(result.message.toolCalls![0].name).toBe('test_tool')
  })

  it('handles API error with retry', async () => {
    mockFetch
      .mockRejectedValueOnce(new Error('OpenAI API error (429): Rate limited'))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          choices: [{ message: { content: 'OK', role: 'assistant' }, finish_reason: 'stop' }],
          usage: { prompt_tokens: 5, completion_tokens: 5, total_tokens: 10 },
        }),
      })

    const result = await adapter.complete([{ role: 'user', content: 'Hi' }])
    expect(result.message.content).toBe('OK')
    expect(mockFetch).toHaveBeenCalledTimes(2)
  })

  it('builds proper request body with tools', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        choices: [{ message: { content: '', role: 'assistant' }, finish_reason: 'stop' }],
        usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
      }),
    })

    await adapter.complete(
      [{ role: 'user', content: 'Do something' }],
      [{ name: 'my_tool', description: 'My tool', parameters: { type: 'object', properties: {} } }],
    )

    const callBody = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(callBody.tools).toHaveLength(1)
    expect(callBody.tools[0].function.name).toBe('my_tool')
    expect(callBody.stream).toBe(true)
  })
})
```

- [ ] **Step 4: 运行 OpenAIAdapter 测试**

Run: `pnpm run test tests/unit/llm-adapter/openai-adapter.spec.ts`

Expected: 通过

- [ ] **Step 5: 运行全量测试验证无回归**

Run: `pnpm run test`

Expected: 所有测试通过

- [ ] **Step 6: Commit**

```bash
git add tests/unit/tools/filesystem/path-utils.spec.ts tests/unit/llm-adapter/openai-adapter.spec.ts
git commit -m "test: add pathUtils and OpenAIAdapter unit tests"
```
