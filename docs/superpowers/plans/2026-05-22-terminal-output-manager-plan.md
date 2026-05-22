# OutputManager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 CLI 终端输出集中到 OutputManager 管理，实现全居中显示和单行 tool 覆盖

**Architecture:** 新增 `OutputManager` 类封装 stdout/stderr 写入，提供居中 padding、`\r` 覆盖、行清空能力。ToolView 改为依赖 OutputManager。index.ts 所有输出点改走 OutputManager。

**Tech Stack:** TypeScript, Node.js (process.stdout), picocolors (已有)

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `apps/cli/src/ui/output-manager.ts` | 新建 | 输出管理器：居中、覆盖、清空 |
| `apps/cli/src/ui/tool-view.ts` | 修改 | 移除 write 回调，改操作 OutputManager |
| `apps/cli/src/index.ts` | 修改 | 创建 OutputManager，所有输出走它 |
| `tests/unit/cli/output-manager.spec.ts` | 新建 | OutputManager 单元测试 |
| `tests/unit/cli/tool-view.spec.ts` | 修改 | 适配单行模式 |

---

### Task 1: 实现 OutputManager

**Files:**
- Create: `apps/cli/src/ui/output-manager.ts`
- Test: `tests/unit/cli/output-manager.spec.ts`

- [ ] **Step 1: 创建 output-manager.ts**

```typescript
import pc from 'picocolors'

function stripAnsi(text: string): string {
  return text.replace(/\x1B\[[0-9;]*m/g, '')
}

export function centerLine(line: string, width: number): string {
  const visible = stripAnsi(line)
  const padding = Math.max(0, Math.floor((width - visible.length) / 2))
  return ' '.repeat(padding) + line
}

export class OutputManager {
  private prevToolLineWidth = 0

  constructor(
    private stdout: NodeJS.WriteStream,
    private stderr: NodeJS.WriteStream,
  ) {}

  get terminalWidth(): number {
    return this.stdout.columns ?? 80
  }

  writeLine(text: string): void {
    const width = this.terminalWidth
    const centered = text
      .split('\n')
      .map((line) => (line.trim() ? centerLine(line, width) : line))
      .join('\n')
    this.stdout.write(centered + '\n')
  }

  writeContent(text: string): void {
    const width = this.terminalWidth
    const centered = text
      .split('\n')
      .map((line) => (line.trim() ? centerLine(line, width) : line))
      .join('\n')
    this.stdout.write(centered + '\n')
  }

  updateToolLine(text: string): void {
    const width = this.terminalWidth
    const padded = centerLine(text, width)
    const lineLen = stripAnsi(padded).length
    const clear = lineLen < this.prevToolLineWidth
      ? ' '.repeat(this.prevToolLineWidth - lineLen)
      : ''
    this.stdout.write('\r' + padded + clear)
    this.prevToolLineWidth = Math.max(lineLen, this.prevToolLineWidth)
  }

  clearToolLine(): void {
    if (this.prevToolLineWidth > 0) {
      this.stdout.write('\r' + ' '.repeat(this.prevToolLineWidth) + '\r')
      this.prevToolLineWidth = 0
    }
  }
}
```

- [ ] **Step 2: 创建 output-manager 测试**

```typescript
import { describe, it, expect, vi } from 'vitest'
import { OutputManager, centerLine } from '../../../apps/cli/src/ui/output-manager.js'

describe('centerLine', () => {
  it('pads short text equally on both sides', () => {
    const result = centerLine('hello', 20)
    expect(result).toBe('       hello        ')
  })

  it('handles text longer than width (no negative padding)', () => {
    const result = centerLine('x'.repeat(100), 40)
    expect(result).toBe('x'.repeat(100))
  })

  it('strips ANSI for visible length calculation', () => {
    const green = '\x1B[32m'
    const reset = '\x1B[39m'
    const result = centerLine(`${green}ok${reset}`, 10)
    expect(result).toBe(`   ${green}ok${reset}   `)
  })

  it('handles empty string', () => {
    expect(centerLine('', 10)).toBe('          ')
  })
})

describe('OutputManager', () => {
  function mockStream(): NodeJS.WriteStream {
    return { write: vi.fn(), columns: 80 } as unknown as NodeJS.WriteStream
  }

  it('writeLine centers output', () => {
    const stdout = mockStream()
    const om = new OutputManager(stdout, {} as NodeJS.WriteStream)
    om.writeLine('hello')
    expect(stdout.write).toHaveBeenCalledWith('                                       hello\n')
  })

  it('updateToolLine uses \\r and no \\n', () => {
    const stdout = mockStream()
    const om = new OutputManager(stdout, {} as NodeJS.WriteStream)
    om.updateToolLine('running')
    expect(stdout.write).toHaveBeenCalledWith('\r' + ' '.repeat(36) + 'running')
  })

  it('clearToolLine writes spaces and \\r', () => {
    const stdout = mockStream()
    const om = new OutputManager(stdout, {} as NodeJS.WriteStream)
    om.updateToolLine('tool')
    vi.mocked(stdout.write).mockClear()
    om.clearToolLine()
    expect(stdout.write).toHaveBeenCalledWith('\r' + ' '.repeat(40) + '\r')
  })

  it('clearToolLine is noop when nothing displayed', () => {
    const stdout = mockStream()
    const om = new OutputManager(stdout, {} as NodeJS.WriteStream)
    om.clearToolLine()
    expect(stdout.write).not.toHaveBeenCalled()
  })

  it('terminalWidth falls back to 80', () => {
    const stdout = { write: vi.fn() } as unknown as NodeJS.WriteStream
    const om = new OutputManager(stdout, {} as NodeJS.WriteStream)
    expect(om.terminalWidth).toBe(80)
  })
})
```

- [ ] **Step 3: 跑测试验证通过**

Run: `npx vitest run tests/unit/cli/output-manager.spec.ts --reporter verbose`
Expected: 7 passed

- [ ] **Step 4: Commit**

```bash
git add apps/cli/src/ui/output-manager.ts tests/unit/cli/output-manager.spec.ts
git commit -m "feat: add OutputManager for centered output and single-line tool overlay"
```

---

### Task 2: 重构 ToolView — 改用 OutputManager

**Files:**
- Modify: `apps/cli/src/ui/tool-view.ts`
- Modify: `tests/unit/cli/tool-view.spec.ts`

- [ ] **Step 1: 更新 tool-view.ts**

```typescript
import pc from 'picocolors'
import type { ToolCall, ToolResult } from '@agent-platform/platform'
import { OutputManager } from './output-manager.js'

const AGENT_LABELS: Record<string, string> = {
  orchestrator: '编排',
  'coding-agent': '编码',
  planner: '规划',
  reviewer: '审查',
  tester: '测试',
}

function agentTag(agentId: string): string {
  const label = AGENT_LABELS[agentId] ?? agentId
  return pc.dim(`[${label}]`)
}

export class ToolView {
  constructor(private om: OutputManager) {}

  onStart(call: ToolCall, agentId: string): void {
    const args = JSON.stringify(call.arguments)
    this.om.updateToolLine(`${agentTag(agentId)} ⎿  ${pc.dim(call.name + '(' + args + ')')}`)
  }

  onFinish(call: ToolCall, result: ToolResult, agentId: string): void {
    if (result.isError) {
      this.om.updateToolLine(`${agentTag(agentId)} ⎿  ${pc.red(call.name + ' error: ' + result.content)}`)
    } else {
      const summary = result.content.length + ' chars'
      this.om.updateToolLine(`${agentTag(agentId)} ⎿  ${pc.green('✓ ' + call.name)} ${pc.dim('(' + summary + ')')}`)
    }
  }

  onRetry(call: ToolCall, attempt: number, maxAttempts: number, agentId: string): void {
    this.om.updateToolLine(`${agentTag(agentId)} ⎿  ${pc.yellow('↻ ' + call.name + ` (retry ${attempt}/${maxAttempts})`)}`)
  }
}
```

- [ ] **Step 2: 更新 tool-view.spec.ts**

```typescript
import { describe, it, expect, vi } from 'vitest'
import { ToolView } from '../../../apps/cli/src/ui/tool-view.js'
import { OutputManager } from '../../../apps/cli/src/ui/output-manager.js'

describe('ToolView', () => {
  function mockToolView(): { om: OutputManager; tv: ToolView } {
    const stdout = { write: vi.fn(), columns: 80 } as unknown as NodeJS.WriteStream
    const om = new OutputManager(stdout, {} as NodeJS.WriteStream)
    const tv = new ToolView(om)
    return { om, tv }
  }

  it('onStart calls updateToolLine with tool call info', () => {
    const { om, tv } = mockToolView()
    const write = vi.spyOn(om, 'updateToolLine')
    tv.onStart({ id: 'tc1', name: 'read_file', arguments: { path: '/f' } }, 'coding-agent')
    expect(write).toHaveBeenCalledTimes(1)
    expect(write.mock.calls[0][0]).toContain('read_file')
  })

  it('onFinish calls updateToolLine with result summary', () => {
    const { om, tv } = mockToolView()
    const write = vi.spyOn(om, 'updateToolLine')
    tv.onFinish(
      { id: 'tc1', name: 'read_file', arguments: { path: '/f' } },
      { content: 'file data', isError: false },
      'coding-agent',
    )
    expect(write).toHaveBeenCalledTimes(1)
    expect(write.mock.calls[0][0]).toContain('read_file')
  })

  it('onFinish with error calls updateToolLine with error', () => {
    const { om, tv } = mockToolView()
    const write = vi.spyOn(om, 'updateToolLine')
    tv.onFinish(
      { id: 'tc1', name: 'read_file', arguments: { path: '/f' } },
      { content: 'error msg', isError: true },
      'coding-agent',
    )
    expect(write.mock.calls[0][0]).toContain('error')
  })

  it('onRetry calls updateToolLine with retry info', () => {
    const { om, tv } = mockToolView()
    const write = vi.spyOn(om, 'updateToolLine')
    tv.onRetry(
      { id: 'tc1', name: 'read_file', arguments: { path: '/f' } },
      1, 3, 'coding-agent',
    )
    expect(write).toHaveBeenCalledTimes(1)
    expect(write.mock.calls[0][0]).toContain('↻')
  })
})
```

- [ ] **Step 3: 跑测试验证**

Run: `npx vitest run tests/unit/cli/tool-view.spec.ts --reporter verbose`
Expected: 4 passed

- [ ] **Step 4: Commit**

```bash
git add apps/cli/src/ui/tool-view.ts tests/unit/cli/tool-view.spec.ts
git commit -m "refactor: ToolView uses OutputManager for single-line overlay"
```

---

### Task 3: Platform.run() 透传 onToolRetry 回调

**Files:**
- Modify: `packages/platform/src/Platform.ts`

`runAgentLoop` 已支持 `onToolRetry`，`ToolExecutionContext` 已包含 `onToolRetry`，但 `Platform.run()` 未接收和透传它。需要补上。

- [ ] **Step 1: Platform.run() 添加 onToolRetry 参数并传给 ctx 和 runAgentLoop**

```typescript
// Platform.ts 约 121-171 行
async run(
  request: string,
  signal?: AbortSignal,
  onChunk?: (text: string) => void,
  onToolStart?: (call: ToolCall, agentId: string) => void,
  onToolFinish?: (call: ToolCall, result: ToolResult, agentId: string) => void,
  onToolRetry?: (call: ToolCall, attempt: number, maxAttempts: number, error: string, agentId: string) => void,
): Promise<AgentResult> {
  // ...
  const ctx = {
    sessionId: session.id,
    agentId: 'orchestrator',
    cwd: session.projectRoot,
    allowedPaths: this.config.security?.allowedPaths ?? [session.projectRoot],
    onToolStart,
    onToolFinish,
    onToolRetry,  // 新增
  }
  // ...
  const result = await runAgentLoop({
    // ... 现有参数 ...
    onToolStart,
    onToolFinish,
    onToolRetry,  // 新增
  })
  // ...
}
```

- [ ] **Step 2: 跑测试确认未破坏**

Run: `npx vitest run`
Expected: Test Files 25 passed (227 tests)

- [ ] **Step 3: Commit**

```bash
git add packages/platform/src/Platform.ts
git commit -m "feat: Platform.run() forwards onToolRetry callback"
```

---

### Task 4: 整合 index.ts — 所有输出走 OutputManager

**Files:**
- Modify: `apps/cli/src/index.ts`

- [ ] **Step 1: 在 index.ts 中创建 OutputManager 并替换所有输出点**

改动位置：创建 `om`、替换 banner 输出、替换 toolView 构造、替换最终结果输出、替换排队/错误输出、注册 onToolRetry。

```typescript
// index.ts 顶部 import 追加
import { OutputManager } from './ui/output-manager.js'

// 在 runCli() 中，创建 platform 后添加
const om = new OutputManager(proc.stdout, proc.stderr)
const toolView = new ToolView(om)
const spinner = new Spinner()

// 替换 banner 输出（约 234 行）
// 原来: cons.log(renderBanner())
// 改为: om.writeContent(renderBanner())

// 分隔线（约 235 行）
// 原来: cons.log(theme.separator('─'.repeat(65)))
// 改为: om.writeLine(theme.separator('─'.repeat(om.terminalWidth)))

// platform.run() 调用（约 250-265 行）
// 在 onToolFinish 后追加 onToolRetry 回调
const result = await platform.run(
  sanitizedInput,
  abortController.signal,
  (chunk) => {
    if (!streamedAny) spinner.stop()
    streamedAny = true
    proc.stdout.write(chunk)  // 保持左对齐流式
  },
  (call, agentId) => {
    spinner.stop()
    toolView.onStart(call, agentId)
  },
  (call, res, agentId) => {
    toolView.onFinish(call, res, agentId)
  },
  (call, attempt, maxAttempts, error, agentId) => {
    toolView.onRetry(call, attempt, maxAttempts, agentId)
  },
)

// 清除 tool 行，输出最终结果
om.clearToolLine()
if (streamedAny) {
  proc.stdout.write('\n')
} else if (result.output) {
  om.writeContent(render(result.output))
} else {
  // 错误信息居中
  const msg = result.status === 'failed'
    ? theme.error(`[LLM temporarily unavailable: ${result.error}] Retry by re-entering your request.`)
    : theme.error(`Error: ${result.error ?? `[${result.status}] No error message provided`}`)
  om.writeLine(msg)
}

// 排队提示
// 原来: cons.log(theme.queue(...))
// 改为: om.writeLine(theme.queue(...))

// 错误
// 原来: cons.log(theme.error(...))
// 改为: om.writeLine(theme.error(...))
```

注意：`Platform.run()` 第 5 个回调参数是 `onToolRetry`，需要确认 `@agent-platform/platform` 导出的 `Platform` 类型已有此参数。

- [ ] **Step 2: 跑全部测试**

Run: `npx vitest run`
Expected: 全部通过

- [ ] **Step 3: 手动验证 UI**

Run: `node apps/cli/dist/cli.js`
触发一次 tool 调用（如写文件），确认：
- tool 调用行覆盖显示，不累积
- 最终结果居中显示
- banner 居中

- [ ] **Step 4: 修复发现的问题**

如有测试失败或 UI 异常，返回修复。

- [ ] **Step 5: Commit**

```bash
git add apps/cli/src/index.ts
git commit -m "feat: integrate OutputManager into CLI main loop"
```

---

## Spec 覆盖率检查

| Spec 需求 | 对应 Task |
|-----------|-----------|
| OutputManager 类设计 | Task 1 |
| `centerLine` + `stripAnsi` | Task 1 |
| `updateToolLine` `\r` 覆盖 | Task 1 |
| `clearToolLine` 行清空 | Task 1 |
| ToolView 改用 OutputManager | Task 2 |
| ToolView.onRetry 支持 | Task 2 |
| index.ts 所有输出居中 | Task 3 |
| 流式 token 左对齐 | Task 4（保留 `proc.stdout.write(chunk)`）|
| 分隔线全宽 | Task 4（`om.terminalWidth`）|
| `onToolRetry` 回调注册 | Task 3（Platform.run）+ Task 4（index.ts 传入）|
| `Platform.run()` 透传 onToolRetry | Task 3 |
| OutputManager 单元测试 | Task 1 Step 2 |
| ToolView 测试更新 | Task 2 Step 2 |
| 已有 227 测试通过 | Task 4 Step 2 |
