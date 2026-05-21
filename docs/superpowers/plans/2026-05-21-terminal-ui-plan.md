# Terminal UI 改造 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将纯文本 CLI 改为 Claude Code 风格的彩色终端界面

**Architecture:** 在 `apps/cli/src/ui/` 下新增 4 个 UI 模块（theme/renderer/spinner/tool-view），在 `runAgentLoop.ts` 和 `Platform.ts` 新增可选回调透传，`index.ts` 接入全部 UI 组件。

**Tech Stack:** picocolors (颜色), marked (Markdown 解析), cli-highlight (代码高亮), ora (spinner)

---

## 文件结构

```
Modified:
  apps/cli/package.json                                — 新增依赖
  apps/cli/src/index.ts                                — 接入 UI 组件
  packages/tool-core/src/runAgentLoop.ts               — 新增 onToolStart/onToolFinish 回调
  packages/platform/src/Platform.ts                    — 透传回调

Create:
  apps/cli/src/ui/theme.ts                             — 颜色常量
  apps/cli/src/ui/renderer.ts                          — Markdown → ANSI
  apps/cli/src/ui/spinner.ts                           — Spinner 封装
  apps/cli/src/ui/tool-view.ts                         — 工具调用可视化

  tests/unit/cli/renderer.spec.ts                      — renderer 测试
  tests/unit/cli/spinner.spec.ts                       — spinner 测试
  tests/unit/cli/tool-view.spec.ts                     — tool-view 测试

Modified tests:
  tests/unit/tool-core/run-agent-loop.spec.ts          — 测试 onToolStart/onToolFinish 回调
  tests/unit/platform/platform.spec.ts                 — 测试 Platform.run() 新参数透传
  tests/unit/platform/cli.spec.ts                      — 适配新 Platform.run 签名
```

---

### Task 1: 安装依赖 + 创建 UI 目录

- [ ] **Step 1: Create UI directory**

```bash
mkdir -p apps/cli/src/ui
```

- [ ] **Step 2: Add dependencies to `apps/cli/package.json`**

```json
{
  "dependencies": {
    "@agent-platform/platform": "workspace:*",
    "picocolors": "^1.1.1",
    "marked": "^15.0.0",
    "cli-highlight": "^2.1.11",
    "ora": "^8.1.0"
  }
}
```

- [ ] **Step 3: Install**

```bash
pnpm install
```

---

### Task 2: 创建 theme.ts

**Create:** `apps/cli/src/ui/theme.ts`

- [ ] **Step 1: Write theme.ts**

```ts
import pc from 'picocolors'

export const theme = {
  prompt:     pc.magenta,
  heading1:   (s: string) => pc.bold(pc.yellow(s)),
  heading2:   (s: string) => pc.bold(pc.cyan(s)),
  bold:       pc.bold,
  inlineCode: (s: string) => pc.bgCyan(pc.white(s)),
  codeFence:  pc.dim,
  blockquote: (s: string) => pc.dim(pc.italic(s)),
  link:       (s: string) => pc.blue(pc.underline(s)),
  filePath:   (s: string) => pc.cyan(pc.underline(s)),
  toolRunning: pc.dim,
  toolDone:   pc.green,
  toolError:  pc.red,
  error:      (s: string) => pc.bold(pc.red(s)),
  queue:      (s: string) => pc.dim(pc.yellow(s)),
  cancel:     pc.dim,
  separator:  pc.dim,
}
```

---

### Task 3: TDD — renderer.ts

**Create:** `apps/cli/src/ui/renderer.ts`
**Create:** `tests/unit/cli/renderer.spec.ts`

- [ ] **Step 1: Write failing test**

```ts
// tests/unit/cli/renderer.spec.ts
import { describe, it, expect } from 'vitest'
import { render } from '../../../apps/cli/src/ui/renderer.js'

describe('renderer', () => {
  it('renders plain text unchanged', () => {
    expect(render('hello world')).toBe('hello world')
  })

  it('renders empty string as empty', () => {
    expect(render('')).toBe('')
  })

  it('renders **bold** text', () => {
    const result = render('hello **world**')
    expect(result).toContain('world')
    expect(result).not.toBe('hello **world**') // ANSI codes present
  })

  it('renders `inline code`', () => {
    const result = render('use `foo()`')
    expect(result).toContain('foo()')
    expect(result).not.toBe('use `foo()`')
  })

  it('renders # heading', () => {
    const result = render('# Title')
    expect(result).toContain('Title')
  })

  it('renders code block with syntax highlighting', () => {
    const result = render('```ts\nconst x = 1\n```')
    expect(result).toContain('const')
    expect(result).toContain('x')
  })

  it('renders code block without language', () => {
    const result = render('```\nplain text\n```')
    expect(result).toContain('plain text')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pnpm run test -- tests/unit/cli/renderer.spec.ts
```
Expected: FAIL — cannot import `render`

- [ ] **Step 3: Write minimal renderer.ts**

```ts
// apps/cli/src/ui/renderer.ts
import { marked } from 'marked'
import { highlight } from 'cli-highlight'
import pc from 'picocolors'

type InlineToken = marked.Token & { tokens?: InlineToken[] }

function renderInline(tokens: InlineToken[]): string {
  return tokens.map((t) => {
    switch (t.type) {
      case 'strong':
        return pc.bold(renderInline(t.tokens ?? []))
      case 'em':
        return pc.italic(renderInline(t.tokens ?? []))
      case 'codespan':
        return pc.bgCyan(pc.white(t.text))
      case 'link':
        return `${pc.blue(pc.underline(t.text))}`
      case 'text':
        return t.text
      default:
        return 'raw' in t ? (t as { raw: string }).raw : ''
    }
  }).join('')
}

function renderBlock(tokens: marked.Token[]): string {
  return tokens.map((t) => {
    switch (t.type) {
      case 'heading':
        return (t.depth === 1 ? pc.bold(pc.yellow) : pc.bold(pc.cyan))(
          renderInline((t as marked.Tokens.Heading).tokens as InlineToken[]),
        ) + '\n'

      case 'paragraph':
        return renderInline((t as marked.Tokens.Paragraph).tokens as InlineToken[]) + '\n\n'

      case 'code': {
        const ct = t as marked.Tokens.Code
        const lang = ct.lang ?? ''
        const header = lang ? pc.dim('```' + lang) : pc.dim('```')
        let body: string
        try {
          body = lang ? highlight(ct.text, { language: lang }) : ct.text
        } catch {
          body = ct.text
        }
        return header + '\n' + body + '\n' + pc.dim('```') + '\n\n'
      }

      case 'blockquote':
        return pc.dim(pc.italic((t as marked.Tokens.Blockquote).text)) + '\n\n'

      case 'list': {
        const lt = t as marked.Tokens.List
        return lt.items.map((item) => {
          const prefix = lt.ordered ? ' 1. ' : ' • '
          return prefix + item.text
        }).join('\n') + '\n\n'
      }

      case 'hr':
        return pc.dim('---') + '\n\n'

      case 'space':
        return '\n'

      default:
        return 'raw' in t ? (t as { raw: string }).raw + '\n' : ''
    }
  }).join('')
}

export function render(text: string): string {
  if (!text) return ''
  const tokens = marked.lexer(text)
  const result = renderBlock(tokens).trimEnd()
  return result || text
}
```

- [ ] **Step 4: Add vitest alias for cli-highlight (if needed)**

Check if tests pass. If `cli-highlight` has ESM issues, add it to vitest config:

```ts
// vitest.config.ts — add to resolve.alias if needed
'cli-highlight': path.resolve(__dirname, 'node_modules/cli-highlight/dist/index.mjs'),
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pnpm run test -- tests/unit/cli/renderer.spec.ts
```
Expected: PASS

---

### Task 4: TDD — spinner.ts

**Create:** `apps/cli/src/ui/spinner.ts`
**Create:** `tests/unit/cli/spinner.spec.ts`

- [ ] **Step 1: Write failing test**

```ts
// tests/unit/cli/spinner.spec.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('Spinner', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('start/stop does not throw', async () => {
    const { Spinner } = await import('../../../apps/cli/src/ui/spinner.js')
    const s = new Spinner()
    expect(() => {
      s.start('working...')
      s.stop()
    }).not.toThrow()
  })

  it('setText after start does not throw', async () => {
    const { Spinner } = await import('../../../apps/cli/src/ui/spinner.js')
    const s = new Spinner()
    s.start('working...')
    expect(() => s.setText('still working...')).not.toThrow()
    s.stop()
  })

  it('double start does not throw', async () => {
    const { Spinner } = await import('../../../apps/cli/src/ui/spinner.js')
    const s = new Spinner()
    s.start('first')
    expect(() => s.start('second')).not.toThrow()
    s.stop()
  })

  it('stop without start does not throw', async () => {
    const { Spinner } = await import('../../../apps/cli/src/ui/spinner.js')
    const s = new Spinner()
    expect(() => s.stop()).not.toThrow()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pnpm run test -- tests/unit/cli/spinner.spec.ts
```
Expected: FAIL — cannot import `Spinner`

- [ ] **Step 3: Write spinner.ts**

```ts
// apps/cli/src/ui/spinner.ts
import ora from 'ora'

export class Spinner {
  private instance?: ora.Ora

  start(text: string): void {
    this.stop()
    this.instance = ora(text).start()
  }

  setText(text: string): void {
    if (this.instance) {
      this.instance.text = text
    }
  }

  stop(): void {
    if (this.instance) {
      this.instance.stop()
      this.instance = undefined
    }
  }
}
```

- [ ] **Step 4: Run tests**

```bash
pnpm run test -- tests/unit/cli/spinner.spec.ts
```
Expected: PASS

---

### Task 5: TDD — tool-view.ts

**Create:** `apps/cli/src/ui/tool-view.ts`
**Create:** `tests/unit/cli/tool-view.spec.ts`

- [ ] **Step 1: Write failing test**

```ts
// tests/unit/cli/tool-view.spec.ts
import { describe, it, expect, vi } from 'vitest'
import { ToolView } from '../../../apps/cli/src/ui/tool-view.js'

describe('ToolView', () => {
  it('onStart outputs formatted tool call line', () => {
    const write = vi.fn()
    const tv = new ToolView(write)
    tv.onStart({ id: 'tc1', name: 'read_file', arguments: { path: '/f' } })
    expect(write).toHaveBeenCalledTimes(1)
    expect(write.mock.calls[0][0]).toContain('read_file')
  })

  it('onFinish outputs result line', () => {
    const write = vi.fn()
    const tv = new ToolView(write)
    tv.onStart({ id: 'tc1', name: 'read_file', arguments: { path: '/f' } })
    write.mockClear()
    tv.onFinish({ id: 'tc1', name: 'read_file', arguments: { path: '/f' } }, { content: 'file data', isError: false })
    expect(write).toHaveBeenCalledTimes(1)
    expect(write.mock.calls[0][0]).toContain('read_file')
  })

  it('onError outputs error line', () => {
    const write = vi.fn()
    const tv = new ToolView(write)
    tv.onStart({ id: 'tc1', name: 'read_file', arguments: { path: '/f' } })
    write.mockClear()
    tv.onFinish({ id: 'tc1', name: 'read_file', arguments: { path: '/f' } }, { content: 'error msg', isError: true })
    expect(write.mock.calls[0][0]).toContain('error')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pnpm run test -- tests/unit/cli/tool-view.spec.ts
```
Expected: FAIL — cannot import `ToolView`

- [ ] **Step 3: Write tool-view.ts**

```ts
// apps/cli/src/ui/tool-view.ts
import pc from 'picocolors'
import type { ToolCall } from '@agent-platform/shared-types'

export class ToolView {
  constructor(private write: (line: string) => void = console.log) {}

  onStart(call: ToolCall): void {
    const args = JSON.stringify(call.arguments)
    this.write(`  ⎿  ${pc.dim(call.name + '(' + args + ')')}`)
  }

  onFinish(call: ToolCall, result: { content: string; isError: boolean }): void {
    if (result.isError) {
      this.write(`  ⎿  ${pc.red(call.name + ' error: ' + result.content)}`)
    } else {
      const summary = result.content.length + ' chars'
      this.write(`  ⎿  ${pc.green('✓ ' + call.name)} ${pc.dim('(' + summary + ')')}`)
    }
  }

}
```

- [ ] **Step 4: Run tests**

```bash
pnpm run test -- tests/unit/cli/tool-view.spec.ts
```
Expected: PASS

---

### Task 6: 添加 onToolStart/onToolFinish 回调到 runAgentLoop

**Modify:** `packages/tool-core/src/runAgentLoop.ts`
**Modify:** `tests/unit/tool-core/run-agent-loop.spec.ts`

- [ ] **Step 1: Add onToolStart/onToolFinish to AgentLoopConfig**

```ts
// packages/tool-core/src/runAgentLoop.ts — in AgentLoopConfig interface
export interface AgentLoopConfig {
  // ... existing fields ...
  onChunk?: (text: string) => void
  onToolStart?: (call: ToolCall) => void
  onToolFinish?: (call: ToolCall, result: { content: string; isError: boolean }) => void
}
```

- [ ] **Step 2: Call them before/after tool execution (around line 84)**

```ts
// packages/tool-core/src/runAgentLoop.ts
for (const call of toolCalls) {
  config.onToolStart?.(call)
  const result = await config.registry.execute(call, config.ctx)
  config.onToolFinish?.(call, result)
  messages.push({
    role: 'tool' as const,
    content: result.content,
    toolResults: [{ content: result.content, isError: result.isError, toolCallId: call.id }],
  })
}
```

- [ ] **Step 3: Add test for callbacks**

```ts
// tests/unit/tool-core/run-agent-loop.spec.ts — add after existing tests
it('calls onToolStart/onToolFinish when tool calls are made', async () => {
  const llm = mockLLM([
    {
      message: {
        role: 'assistant',
        content: 'checking...',
        toolCalls: [{ id: 'tc1', name: 'read_file', arguments: { path: '/f' } }],
      },
      usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
      finishReason: 'tool_calls',
    },
    {
      message: { role: 'assistant', content: 'Done' },
      usage: { promptTokens: 20, completionTokens: 10, totalTokens: 30 },
      finishReason: 'stop',
    },
  ])
  const registry = mockRegistry(['content'])
  const onToolStart = vi.fn()
  const onToolFinish = vi.fn()

  await runAgentLoop({
    agent,
    messages: [msg('user', 'read')],
    llm,
    registry,
    ctx: { sessionId: 's1', agentId: 'a1', cwd: '/tmp' },
    onToolStart,
    onToolFinish,
  })

  expect(onToolStart).toHaveBeenCalledTimes(1)
  expect(onToolStart).toHaveBeenCalledWith({ id: 'tc1', name: 'read_file', arguments: { path: '/f' } })
  expect(onToolFinish).toHaveBeenCalledTimes(1)
  expect(onToolFinish).toHaveBeenCalledWith(
    { id: 'tc1', name: 'read_file', arguments: { path: '/f' } },
    { content: 'content', isError: false },
  )
})
```

- [ ] **Step 4: Run tests**

```bash
pnpm run test -- tests/unit/tool-core/run-agent-loop.spec.ts
```
Expected: PASS

---

### Task 7: 透传回调到 Platform.run()

**Modify:** `packages/platform/src/Platform.ts`
**Modify:** `tests/unit/platform/platform.spec.ts`

- [ ] **Step 1: Update Platform.run() signature and pass through**

```ts
// packages/platform/src/Platform.ts
import type { ToolCall } from '@agent-platform/shared-types'

async run(
  request: string,
  signal?: AbortSignal,
  onChunk?: (text: string) => void,
  onToolStart?: (call: ToolCall) => void,
  onToolFinish?: (call: ToolCall, result: { content: string; isError: boolean }) => void,
): Promise<AgentResult> {
  try {
    if (signal?.aborted) {
      return { status: 'aborted', agentId: 'orchestrator' }
    }

    const session = this.createSession('orchestrator', process.cwd())
    const ctx = {
      sessionId: session.id,
      agentId: 'orchestrator',
      cwd: session.projectRoot,
      allowedPaths:
        this.config.security?.allowedPaths ?? [session.projectRoot],
    }

    const messages = [{ role: 'user' as const, content: request }]

    const result = await runAgentLoop({
      agent: this.orchestratorAgent,
      messages,
      registry: this.registry,
      ctx,
      llm: this.llm,
      memory: session.stm,
      maxIterations: this.config.runtime?.maxIterations,
      compressionRatio: this.config.runtime?.compressionRatio,
      contextWindow: this.orchestratorAgent.contextWindow,
      signal,
      onChunk,
      onToolStart,
      onToolFinish,
    })

    return result
  } catch (e) {
    return {
      status: 'failed',
      agentId: 'orchestrator',
      error: (e as Error).message,
    }
  }
}
```

- [ ] **Step 2: Verify platform.spec.ts needs no changes**

检查 `tests/unit/platform/platform.spec.ts`：所有测试都 mock 了 `runAgentLoop` 并只检查返回值，不检查 `runAgentLoop` 的参数。`Platform.run()` 新参数 `onToolStart`/`onToolFinish` 是可选的回调，不影响现有 mock 的调用。所以**不需要改 platform.spec.ts**。

- [ ] **Step 3: Run tests**

```bash
pnpm run test -- tests/unit/platform/
```
Expected: PASS

---

### Task 8: 接入 CLI — 修改 index.ts

**Modify:** `apps/cli/src/index.ts`
**Modify:** `tests/unit/platform/cli.spec.ts`

- [ ] **Step 1: Update imports at top of index.ts**

```ts
// apps/cli/src/index.ts — add to imports
import { theme } from './ui/theme.js'
import { Spinner } from './ui/spinner.js'
import { ToolView } from './ui/tool-view.js'
import { render } from './ui/renderer.js'
```

- [ ] **Step 2: Move `rl` creation after platform init, use colored prompt**

```ts
const platform = new PlatformCtor(config)

const toolView = new ToolView()
const spinner = new Spinner()

const promptText = theme.prompt('> ') + (config.cli?.prompt ?? 'Ask me anything: ')
const rl = rlMod.createInterface({
  input: proc.stdin,
  output: proc.stdout,
  prompt: promptText,
})
```

- [ ] **Step 3: Update SIGINT handler to stop spinner**

```ts
proc.on('SIGINT', () => {
  spinner.stop()
  abortController.abort()
  pendingQueue = []
  cons.log('\nExiting...')
  proc.exit(0)
})
```

- [ ] **Step 4: Update ESC keypress handler with colored messages**

```ts
if (proc.stdin.isTTY) {
  readline.emitKeypressEvents(proc.stdin)
  proc.stdin.setRawMode(true)

  proc.stdin.on('keypress', (_str: string, key: { name?: string }) => {
    if (key?.name === 'escape' && pendingQueue.length > 0) {
      pendingQueue = []
      cons.log('\n' + theme.cancel('[排队已取消]'))
      rl.prompt()
    }
  })
}
```

- [ ] **Step 5: Update processInput — pass onToolStart/onToolFinish and add spinner + render**

```ts
async function processInput(input: string) {
  const sanitizedInput = input.trim()
  if (!sanitizedInput) {
    rl.prompt()
    return
  }

  running = true
  spinner.start('思考中...')
  try {
    let streamedAny = false
    const result = await platform.run(
      sanitizedInput,
      abortController.signal,
      (chunk) => {
        streamedAny = true
        proc.stdout.write(chunk)
      },
      (call) => {
        spinner.stop()
        toolView.onStart(call)
      },
      (call, res) => {
        toolView.onFinish(call, res)
      },
    )

    spinner.stop()

    if (result.status === 'aborted') {
      return
    }

    if (streamedAny) {
      proc.stdout.write('\n')
    } else if (result.output) {
      cons.log(render(result.output))
    } else {
      const msg =
        result.status === 'failed'
          ? theme.error(`[LLM temporarily unavailable: ${result.error}] Retry by re-entering your request.`)
          : theme.error(`Error: ${result.error}`)
      cons.error(msg)
    }
  } catch (e) {
    spinner.stop()
    if ((e as Error).name === 'AbortError') return
    cons.error(theme.error(`Platform error: ${(e as Error).message}`))
  } finally {
    running = false
    if (pendingQueue.length > 0) {
      const next = pendingQueue.shift()!
      processInput(next)
    } else {
      rl.prompt()
    }
  }
}
```

- [ ] **Step 6: Update queue message with color**

```ts
cons.log(theme.queue(`⏳ 任务已排队 (${pendingQueue.length} 个待处理). 按 ESC 取消排队`))
```

- [ ] **Step 7: Update exit handler**

```ts
proc.on('exit', () => {
  spinner.stop()
  if (proc.stdin.isTTY) {
    proc.stdin.setRawMode(false)
  }
})
```

- [ ] **Step 8: Update cli.spec.ts to adapt platform mock**

The existing CLI tests mock `PlatformCtor` and return `{ run: runMock }`. The `runMock` currently receives 3 args. After our change, it receives 5 args. The existing mocks use `mockImplementation(() => ({ run: runMock }))` and `runMock` is `vi.fn()` which accepts any args — so existing tests should still pass.

Verify:

```bash
pnpm run test -- tests/unit/platform/cli.spec.ts
```
Expected: PASS

---

### Task 9: 构建 + 全面验证

- [ ] **Step 1: Build**

```bash
pnpm run build
```
Expected: tsc passes, esbuild produces `apps/cli/dist/cli.js`

- [ ] **Step 2: Run full test suite**

```bash
pnpm run test
```
Expected: all tests PASS, coverage ≥ 80%

- [ ] **Step 3: Lint**

```bash
pnpm run lint
```
Expected: 0 warnings, 0 errors

- [ ] **Step 4: Manual smoke test**

需要先设置 `ANTHROPIC_API_KEY`（或已有 `~/.agent-platform/config.json`）：

```bash
export ANTHROPIC_API_KEY=sk-...
node apps/cli/dist/cli.js
```
Expected: CLI starts with colored `> ` prompt, shows spinner during LLM call, tool calls displayed in dim/green, response text with formatted markdown and syntax-highlighted code blocks.
