# Code Review Fixes 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复代码审查中发现的 12 个问题，按 severity 依次修复

**架构思路：** 所有改动限于现有文件内，不新增文件。Critical 问题优先——修复 STM/消息存储分离（`runAgentLoop.ts`）和 abort 传播（`delegateTool.ts`）。Important 问题主要为死代码删除、配置穿透、测试健壮性。

**Tech Stack:** TypeScript + vitest + pnpm workspace

**执行顺序：** Task 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10（严格串行，每个任务完成后 `pnpm run test` 全绿才继续）

**测试策略：** 已在 `tests/unit/tool-core/run-agent-loop.spec.ts` 中有 token budget + STM compact 的测试（describe('token budget + STM compact (Step 5.3)')）。修改前先运行确认这些测试通过，修改后补充新测试覆盖修复的行为。

---

### Task 1: 修复 STM/消息存储分离 + token 预算（Critical）

**根因：** `runAgentLoop` 使用本地 `messages` 数组存储对话，但从不调用 `memory.add()`。当 `memory.compact()` 释放 token 预算时，释放的只是 STM 内部消息的空间，本地 `messages` 数组仍无限增长。最终 `totalTokens > budget` 时循环直接返回 `failed`，而不是优雅压缩。

**修复方案：** 让 local `messages` 数组与 STM 保持同步。每次迭代后将新消息写入 STM；compact 成功后用 STM 的 `getContext()` 替换 local `messages` 的对应段。

**Files:**
- Modify: `packages/tool-core/src/runAgentLoop.ts`
- Test: `tests/unit/tool-core/run-agent-loop.spec.ts`

- [ ] **Step 1: 读取当前代码，理解本地 messages 与 STM 的关系**

  `packages/tool-core/src/runAgentLoop.ts` — 当前 state after-iteration 代码（lines 70-83）：
  ```
  messages.push({ role: 'assistant', content, toolCalls })
  for (const call of toolCalls) {
    const result = await config.registry.execute(call, config.ctx)
    messages.push({ role: 'tool', content, toolResults })
  }
  ```
  Token budget 代码（lines 85-112）：
  ```
  if (config.memory) {
    totalTokens += response.usage.totalTokens
    if (totalTokens > budget * 1.5 && consecutiveCompactFailures >= 3) break
    if (totalTokens > budget) {
      const freed = config.memory.compact()
      if (freed > 0) totalTokens -= freed
      else consecutiveCompactFailures++
    }
  }
  ```
  **问题：** `memory.compact()` 释放了 STM 内部的消息，但 local `messages` 从未截断。下次迭代发送给 LLM 的消息仍是完整的未压缩历史。

- [ ] **Step 2: 修改 runAgentLoop——每次迭代后将新消息同步到 memory**

  在 assistant 消息和 tool 结果推入 local `messages` 后，也调用 `memory.add()`：
  ```typescript
  messages.push({
    role: 'assistant' as const,
    content: response.message.content ?? '',
    toolCalls,
  })

  for (const call of toolCalls) {
    const result = await config.registry.execute(call, config.ctx)
    messages.push({
      role: 'tool' as const,
      content: result.content,
      toolResults: [{ content: result.content, isError: result.isError }],
    })
  }

  if (config.memory) {
    config.memory.add(messages[messages.length - toolCalls.length - 1])
    for (let i = toolCalls.length; i > 0; i--) {
      config.memory.add(messages[messages.length - i])
    }
  }
  ```

- [ ] **Step 3: 修改 compact 成功后同步回 local messages**

  当 `memory.compact()` 返回 `freed > 0` 时，用 STM 的当前上下文替换 local `messages` 的开头部分：
  ```typescript
  if (totalTokens > budget) {
    const freed = config.memory.compact()
    if (freed > 0) {
      totalTokens = Math.max(0, totalTokens - freed)
      consecutiveCompactFailures = 0
      // 将 STM 压缩后的消息同步回 local messages
      const stmContext = config.memory.getContext()
      // 保留最新的一轮未压缩对话（assistant + tool results），其余用 STM 消息替换
      const keepCount = toolCalls.length + 1  // assistant msg + each tool result
      const recent = messages.splice(-keepCount)
      messages = [...stmContext, ...recent]
    }
  }
  ```
  注意：`messages` 需要改为 `let` 声明（当前为 `const messages = [...config.messages]`）。

- [ ] **Step 4: 修复 messages 声明为 let**

  第 29 行改为：
  ```typescript
  let messages = [...config.messages]
  ```

- [ ] **Step 5: 更新 token budget 测试——验证 compact 后 messages 变短**

  在 `tests/unit/tool-core/run-agent-loop.spec.ts` 的 `describe('token budget + STM compact')` 中追加测试：
  ```typescript
  it('compact syncs back to local messages array', async () => {
    const stm = new ShortTermMemory()
    // 填满 STM 使其可压缩
    for (let i = 0; i < 60; i++) {
      stm.add({ role: 'user', content: 'padding '.repeat(20) })
    }

    const toolResponse: ChatResponse = {
      message: {
        role: 'assistant',
        content: 'thinking...',
        toolCalls: [{ id: 'tc1', name: 'read_file', arguments: { path: '/f' } }],
      },
      usage: { promptTokens: 100, completionTokens: 50, totalTokens: 150 },
      finishReason: 'tool_calls',
    }

    const llm = mockLLM([
      toolResponse,
      {
        message: { role: 'assistant', content: 'done' },
        usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
        finishReason: 'stop',
      },
    ])

    // 预算 = 200 * 0.5 = 100，第一次迭代 150 > 100 → 触发 compact
    await runAgentLoop({
      agent,
      messages: [msg('user', 'Do it')],
      llm,
      registry: mockRegistry(['result']),
      ctx: { sessionId: 's1', agentId: 'a1', cwd: '/tmp' },
      memory: stm,
      contextWindow: 200,
      compressionRatio: 0.5,
      maxIterations: 10,
    })

    // 验证：第二次迭代时 LLM 收到的消息数应该少于第一次（被压缩了）
    // llm.complete 第二次调用的参数应包含 system prompt 压缩摘要
    const secondCallArgs = llm.complete.mock.calls[1][0] as ChatMessage[]
    const hasSummary = secondCallArgs.some(
      (m) => m.role === 'system' && m.content.includes('[User Messages]'),
    )
    expect(hasSummary).toBe(true)
  })
  ```

- [ ] **Step 6: 运行全部测试验证**

  ```bash
  pnpm run test
  ```
  Expected: 全部通过，无回归

---

### Task 2: 修复 abort 未传播（Critical）

**根因：** `DelegateToAgentHandler.execute()` 中 `runAgentLoop` 返回 `status: 'aborted'` 时，handler 仍返回 `{ isError: false }` 的 JSON，orchestrator 无法感知中止。

**Files:**
- Modify: `packages/platform/src/tools/delegateTool.ts`
- Test: `tests/unit/platform/delegate-tool.spec.ts`

- [ ] **Step 1: 修改 delegateTool.ts**

  在 `delegateTool.ts` 第 69-77 行，添加 abort 检查：
  ```typescript
  const result = await runAgentLoop({
    agent: targetAgent,
    messages: fullMessages,
    registry: this.registry,
    ctx: delegateCtx,
    llm: this.llm,
    memory: stm,
    compressionRatio: this.compressionRatio,
  })

  if (result.status === 'aborted') {
    return { content: 'Sub-agent aborted', isError: true }
  }

  return {
    content: JSON.stringify({ agentId: args.agentId, output: result.output }),
    isError: false,
  }
  ```

- [ ] **Step 2: 补充测试**

  在 `tests/unit/platform/delegate-tool.spec.ts` 中追加：
  ```typescript
  it('returns isError when sub-agent is aborted', async () => {
    vi.resetModules()
    const { runAgentLoop } = await import('@agent-platform/tool-core')
    ;(runAgentLoop as ReturnType<typeof vi.fn>).mockResolvedValue({
      status: 'aborted',
      agentId: 'coding-agent',
    })

    const { DelegateToAgentHandler } = await import('@agent-platform/platform')
    const codingAgent: Agent = {
      id: 'coding-agent', name: 'CA', description: '', systemPrompt: '',
      model: 'claude-sonnet-4', tools: [],
    }
    const handler = new DelegateToAgentHandler(
      { get: vi.fn().mockReturnValue(codingAgent) },
      { complete: vi.fn() },
      { register: vi.fn(), getAllTools: vi.fn().mockReturnValue([]), execute: vi.fn() },
    )
    const result = await handler.execute(
      { id: 'c1', name: 'delegate_to_agent', arguments: { agentId: 'coding-agent', task: 'do' } },
      { sessionId: 's1', agentId: 'orchestrator', cwd: '/p' },
    )
    expect(result.isError).toBe(true)
    expect(result.content).toContain('aborted')
  })
  ```

- [ ] **Step 3: 运行全部测试验证**

  ```bash
  pnpm run test
  ```
  Expected: 全部通过

---

### Task 3: 删除 FilesystemHandler 冗余路径校验（Important）

**根因：** `FilesystemHandler.checkAllowed()` 是 ToolRegistry 全局校验的重复实现，且功能更弱（只检查顶层 path/filepath，不递归）。

**Files:**
- Modify: `packages/tools/filesystem/src/FilesystemHandler.ts`
- Test: `tests/unit/tools/filesystem/filesystem-handler.spec.ts`

- [ ] **Step 1: 删除 `checkAllowed` 函数及调用**

  删除 `FilesystemHandler.ts` 中：
  - `checkAllowed` 函数（lines 68-80）
  - execute() 中的 `const denied = checkAllowed(args, ctx); if (denied) return denied;`（lines 123-124）

- [ ] **Step 2: 同步删除外部 allowedPaths 的 ENOENT 检查**

  `allowedPaths` 相关测试在 `tests/unit/tools/filesystem/filesystem-handler.spec.ts` 中（`write_file` 和 `edit_file` 的 "returns Access denied" 测试），删除这两条测试：
  - `write_file` describe 中的 `'outside allowedPaths returns Access denied'`（lines 180-188）
  - `edit_file` describe 中的 `'outside allowedPaths returns Access denied'`（lines 254-267）

- [ ] **Step 3: 运行全部测试验证**

  ```bash
  pnpm run test
  ```
  Expected: 全部通过，删除的测试对应的行为由 ToolRegistry 测试覆盖

---

### Task 4: stmThreshold 配置穿透（Important）

**根因：** `RuntimeConfig.stmThreshold` 定义在 config 中，但 `runAgentLoop` 从未读取或传递给 `ShortTermMemory` 构造函数。

**Files:**
- Modify: `packages/tool-core/src/runAgentLoop.ts`
- Modify: `packages/platform/src/Platform.ts`

- [ ] **Step 1: 在 AgentLoopConfig 中添加 stmThreshold 字段**

  `packages/tool-core/src/runAgentLoop.ts` 的 `AgentLoopConfig` 接口中追加：
  ```typescript
  export interface AgentLoopConfig {
    // ... 现有字段
    stmThreshold?: number
  }
  ```

- [ ] **Step 2: 在 Platform.run() 中传递 stmThreshold**

  `packages/platform/src/Platform.ts` 第 109-119 行的 `runAgentLoop` 调用：
  ```typescript
  const result = await runAgentLoop({
    agent: this.orchestratorAgent,
    messages,
    registry: this.registry,
    ctx,
    llm: this.llm,
    memory: session.stm,
    maxIterations: this.config.runtime?.maxIterations,
    compressionRatio: this.config.runtime?.compressionRatio,
    stmThreshold: this.config.runtime?.stmThreshold,  // 追加
    signal,
  })
  ```

- [ ] **Step 3: 在 runAgentLoop 中使用 stmThreshold**

  `runAgentLoop.ts` 的 loop 开始时，如果有 memory 且有 stmThreshold，动态调整 STM 的 threshold（但 STM 的 threshold 目前是构造函数参数且没有 setter。更简单的方式：在第一次 compact 前如果 stmThreshold 与默认不同，重建 STM 对象）。

  实际上 simplest 方式：
  ```typescript
  // 在 runAgentLoop 函数开头，config.memory 创建后
  // STM 的 threshold 只在构造函数设置，无法运行时修改
  // 改用传递给 config.memory 的 compact 方法时附带 threshold
  ```

  但 `ShortTermMemory.compact()` 不接收参数。最优方案是在 `AgentLoopConfig` 中声明但暂不传递——因为在 `Platform` 创建 `ShortTermMemory` 时已有 threshold 控制。

  更准确的修复：`Platform.createSession()` 已经创建了 `new ShortTermMemory()`（默认 threshold=50），只需将 `config.runtime.stmThreshold` 传递给构造函数：

  `Platform.ts` 中 `createSession`：
  ```typescript
  createSession(agentId: string, projectRoot: string): Session {
    return {
      id: randomUUID(),
      agentId,
      projectRoot,
      stm: new ShortTermMemory(0, this.config.runtime?.stmThreshold ?? 50),
    }
  }
  ```

- [ ] **Step 4: 运行全部测试验证**

  ```bash
  pnpm run test
  ```

---

### Task 5: contextWindow 配置一致性（Important）

**根因：** `AgentLoopConfig.contextWindow` 优先于 `agent.contextWindow`，但 `Platform.run()` 从不设置它，导致 user 无法通过 config 调整。

**Files:**
- Modify: `packages/platform/src/Platform.ts`

- [ ] **Step 1: Platform.run() 传递 contextWindow**

  `packages/platform/src/Platform.ts` 在 `runAgentLoop` 调用中追加：
  ```typescript
  const result = await runAgentLoop({
    agent: this.orchestratorAgent,
    messages,
    registry: this.registry,
    ctx,
    llm: this.llm,
    memory: session.stm,
    maxIterations: this.config.runtime?.maxIterations,
    compressionRatio: this.config.runtime?.compressionRatio,
    contextWindow: this.orchestratorAgent.contextWindow,  // 明确传入
    stmThreshold: this.config.runtime?.stmThreshold,
    signal,
  })
  ```

  当前 `this.orchestratorAgent.contextWindow` 来自 `DEFAULT_AGENT_PARAMS.contextWindow`（200000），和 `AgentLoopConfig` 的默认值一致。此改动只是让优先级明确化——`agent.contextWindow` 优先于 `runAgentLoop` 内部的兜底默认值。

- [ ] **Step 2: 运行全部测试验证**

  ```bash
  pnpm run test
  ```

---

### Task 6: 修复 delegate-tool.spec.ts 测试隔离（Important）

**根因：** `vi.resetModules()` 在测试 body 中调用而不是 `beforeEach`，可能导致跨测试污染。

**Files:**
- Modify: `tests/unit/platform/delegate-tool.spec.ts`

- [ ] **Step 1: 将 resetModules 移到 beforeEach**

  修改 `tests/unit/platform/delegate-tool.spec.ts`：
  - 在 `describe('DelegateToAgentHandler')` 内添加 `beforeEach(() => { vi.resetModules() })`
  - 删除第 82 行的 `vi.resetModules()` 内联调用

- [ ] **Step 2: 运行全部测试验证**

  ```bash
  pnpm run test
  ```
  Expected: 全部通过，无测试顺序依赖

---

### Task 7: execFile 中包含 stderr 输出（Important）

**根因：** `GitHandler` 和 `TerminalHandler` 的 `execFile` 回调忽略 `stderr`。命令在退出码 0 的同时写入 stderr 的警告信息会被静默丢弃。

**Files:**
- Modify: `packages/tools/git/src/GitHandler.ts`
- Modify: `packages/tools/terminal/src/TerminalHandler.ts`
- Test: `tests/unit/tools/git/git-handler.spec.ts`
- Test: `tests/unit/tools/terminal/terminal-handler.spec.ts`

- [ ] **Step 1: 修改 GitHandler execGit 函数**

  `GitHandler.ts` lines 16-30，修改回调以包含 stderr：
  ```typescript
  function execGit(
    args: string[], cwd: string, timeout: number,
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      execFile('git', args, { cwd, timeout }, (err, stdout, stderr) => {
        if (err) {
          reject(err)
        } else {
          const output = stderr ? `${stdout}\n[stderr]\n${stderr}`.trim() : stdout
          resolve(output)
        }
      })
    })
  }
  ```

- [ ] **Step 2: 修改 TerminalHandler execFile 回调**

  `TerminalHandler.ts` lines 94-111：
  ```typescript
  const output = await new Promise<string>((resolve, reject) => {
    execFile(name, cmdArgs, { cwd: ctx.cwd, timeout: 30000, maxBuffer: 20 * 1024 },
      (err, stdout, stderr) => {
        if (err) {
          reject(err)
        } else {
          const result = stderr ? `${stdout}\n[stderr]\n${stderr}`.trim() : stdout
          resolve(result)
        }
      },
    )
  })
  ```

- [ ] **Step 3: 更新 TerminalHandler 测试——验证 execFile 参数的 maxBuffer 断言**

  当前 `terminal-handler.spec.ts:140-143` 断言 `opts.maxBuffer` 是 `20 * 1024`。由于 `maxBuffer` 定义本身未变，此测试应继续通过。但需确认 stderr 包含不影响现有测试（mock 的 stderr 是空字符串）。

- [ ] **Step 4: 运行全部测试验证**

  ```bash
  pnpm run test
  ```

---

### Task 8: grep/grep_r 优雅处理非法正则表达式（Minor）

**根因：** `grep` 和 `grep_r` 中 `new RegExp(pattern)` 抛出的异常由外层 catch 捕获，返回不友好的原始错误消息。

**Files:**
- Modify: `packages/tools/filesystem/src/FilesystemHandler.ts`
- Test: `tests/unit/tools/filesystem/filesystem-handler.spec.ts`

- [ ] **Step 1: 在 grep 和 grep_r 中包装 RegExp 构造**

  `FilesystemHandler.ts` 中 `grep()`（line 188）和 `grepR()`（line 209）的 `new RegExp(pattern)` 分别用 try/catch 包裹：
  ```typescript
  // grep 方法（line 188）
  let regex: RegExp
  try {
    regex = new RegExp(pattern)
  } catch {
    return { content: `Invalid regex pattern: ${pattern}`, isError: true }
  }

  // grepR 方法（line 209）
  let regex: RegExp
  try {
    regex = new RegExp(pattern)
  } catch {
    return { content: `Invalid regex pattern: ${pattern}`, isError: true }
  }
  ```

- [ ] **Step 2: 补充测试**

  在 `tests/unit/tools/filesystem/filesystem-handler.spec.ts` 的 `grep` describe 中追加：
  ```typescript
  it('returns isError for invalid regex pattern', async () => {
    const filePath = join(dir, 'test.txt')
    writeFileSync(filePath, 'abc', 'utf-8')
    const result = await handler.execute(
      { id: '1', name: 'grep', arguments: { pattern: '[invalid', path: filePath } },
      ctx(dir),
    )
    expect(result.isError).toBe(true)
    expect(result.content).toContain('Invalid regex')
  })
  ```

  `grep_r` describe 中追加：
  ```typescript
  it('returns isError for invalid regex pattern', async () => {
    const result = await handler.execute(
      { id: '1', name: 'grep_r', arguments: { pattern: '[invalid', path: dir } },
      ctx(dir),
    )
    expect(result.isError).toBe(true)
    expect(result.content).toContain('Invalid regex')
  })
  ```

- [ ] **Step 3: 运行全部测试验证**

  ```bash
  pnpm run test
  ```

---

### Task 9: listDir 不友好错误消息（Minor）

**根因：** `listDir` 不像 `readFile` 那样显式处理 ENOENT。

**Files:**
- Modify: `packages/tools/filesystem/src/FilesystemHandler.ts`

- [ ] **Step 1: 在 listDir 中添加 ENOENT 处理**

  `FilesystemHandler.ts` 中 `listDir`（lines 178-185）添加 ENOENT 检查：
  ```typescript
  private listDir(path: string): ToolResult {
    try {
      const entries = readdirSync(path, { withFileTypes: true })
      const result = entries.map((e) => ({
        name: e.name,
        type: e.isDirectory() ? 'directory' as const : 'file' as const,
      }))
      return { content: JSON.stringify(result), isError: false }
    } catch (e) {
      const nodeErr = e as NodeJS.ErrnoException
      if (nodeErr.code === 'ENOENT') {
        return {
          content: `ENOENT: no such file or directory '${path}'`,
          isError: true,
        }
      }
      throw e
    }
  }
  ```

- [ ] **Step 2: 运行全部测试验证**

  ```bash
  pnpm run test
  ```

---

### Task 10: 迁移 FilesystemHandler 到 fs.promises（Minor）

**根因：** 所有文件操作用同步 `*Sync` API，大文件时会阻塞事件循环。方法签名已是 `async`。

**Files:**
- Modify: `packages/tools/filesystem/src/FilesystemHandler.ts`
- Test: `tests/unit/tools/filesystem/filesystem-handler.spec.ts`

- [ ] **Step 1: 将 import 从 `node:fs` 改为 `node:fs/promises`**

  ```typescript
  import {
    readFile, readdir, stat, writeFile,
  } from 'node:fs/promises'
  import { existsSync } from 'node:fs'  // 保留 existsSync（无 promise 版本）
  ```

- [ ] **Step 2: 逐个方法从 Sync 改为 async**

  - `readFile`: `readFileSync(path, 'utf-8')` → `await readFile(path, 'utf-8')`
  - `listDir`: `readdirSync(path, { withFileTypes: true })` → `await readdir(path, { withFileTypes: true })`
  - `grep`: `readFileSync(filePath, 'utf-8')` → `await readFile(filePath, 'utf-8')`
  - `grepR`: `readdirSync(dir)` → `await readdir(dir)`，`statSync(fullPath)` → `await stat(fullPath)`，`readFileSync(fullPath, 'utf-8')` → `await readFile(fullPath, 'utf-8')`。注意 walk 函数改为 `async`，递归调用改为 `await walk(fullPath)`
  - `writeFile`: `writeFileSync(path, content, 'utf-8')` → `await writeFile(path, content, 'utf-8')`
  - `editFile`: `readFileSync(path, 'utf-8')` → `await readFile(path, 'utf-8')`，`writeFileSync(path, updated, 'utf-8')` → `await writeFile(path, updated, 'utf-8')`

- [ ] **Step 3: 测试中验证文件写入后读取——改为 await 方式**

  测试中 `existsSync(filePath)` 无需改动（`existsSync` 保留在 `node:fs` import 中）。
  
  `writeFile` 测试中验证写入内容的 import 方式（line 165, 176, 204, 234）——当前已是 dynamic import `node:fs` 的 `readFileSync`，可保留。

- [ ] **Step 4: 运行全部测试验证**

  ```bash
  pnpm run test
  ```

---

## 验收标准

全部任务完成后：

- [ ] `pnpm run build` — 零错误
- [ ] `pnpm run lint` — 零警告
- [ ] `pnpm run test` — 全部通过，覆盖率 ≥ 80%
- [ ] `pnpm run build` 产物 `apps/cli/dist/cli.js` 正常生成

