# OutputManager — 终端输出统一管理

## 概述

将 CLI 的终端输出集中到 `OutputManager` 管理，实现：
1. **全居中显示** — 所有输出（tool 调用、AI 回答、banner）水平居中
2. **单行 tool 覆盖** — 工具调用只显示最新一行，新调用覆盖旧调用

## 改动范围

| 文件 | 改动 |
|------|------|
| `apps/cli/src/ui/output-manager.ts` | **新增** — OutputManager 类 |
| `apps/cli/src/ui/tool-view.ts` | 重构 — 改为单行覆盖模式 |
| `apps/cli/src/ui/spinner.ts` | 适配 — 与 OutputManager 协调输出 |
| `apps/cli/src/index.ts` | 重构 — 所有输出走 OutputManager |
| `tests/unit/cli/output-manager.spec.ts` | **新增** — OutputManager 测试 |
| `tests/unit/cli/tool-view.spec.ts` | 更新 — 适配单行模式 |

## OutputManager 设计

```typescript
class OutputManager {
  constructor(private stdout: NodeJS.WriteStream, private stderr: NodeJS.WriteStream)

  // 居中写入一行（自动 padding）
  writeLine(text: string): void
  // 居中写入多行内容（如 markdown 渲染结果）
  writeContent(text: string): void
  // 更新 tool 状态行（\r 覆盖）
  updateToolLine(text: string): void
  // 清空 tool 状态行
  clearToolLine(): void
  // 获取终端宽度
  get terminalWidth(): number  // process.stdout.columns ?? 80
}
```

### 居中算法

不新增外部依赖。picocolors 只输出 `\x1B[...m`（SGR）码，用内联正则即可：

```typescript
function stripAnsi(text: string): string {
  return text.replace(/\x1B\[[0-9;]*m/g, '')
}

function centerLine(line: string, width: number): string {
  const visible = stripAnsi(line)
  const padding = Math.max(0, Math.floor((width - visible.length) / 2))
  return ' '.repeat(padding) + line
}
```

- 先按 `\n` 拆行，每行独立计算 padding
- 空行不 padding（保持空白）
- 对超长行不截断（左对齐兜底）

### 单行 Tool 覆盖

```
写入时序：

  tool 开始 → updateToolLine("  [编码] ⎿  exec_command({...})")   ← \r 覆盖
  tool 结束 → updateToolLine("  [编码] ⎿  ✓ exec_command (10 chars)")
  下一个    → updateToolLine("  [编码] ⎿  exec_command({...})")   ← \r 覆盖同一行
  最终结果  → clearToolLine() + writeContent(result)
```

实现：
- `updateToolLine()` 用 `\r` + padding + 内容（不加 `\n`）
- 行尾用空格填充到上一行长度，确保完全覆盖旧内容
- `clearToolLine()` 用 `\r` + 空格填满整行 + `\r` 回到行首

### 与 Spinner 协调

Spinner（ora）写入 stderr，OutputManager 写 stdout，互不冲突。
但 tool 行出现在 stdout 上。当 spinner 运行时 tool 行应保持可见。

新流程：

```
processInput():
  1. spinner.start('思考中...')       → stderr 动画
  2. tool 开始 → spinner.stop()
                om.updateToolLine(...)  → stdout 单行
  3. tool 结束 → om.updateToolLine(...) → stdout 更新同一行
  4. spinner.start('思考中...')       → stderr 动画（tool 行保留在 stdout）
  5. 重复 2-4 直到 LLM 返回最终结果
  6. om.clearToolLine()               → 清除 tool 行
  7. om.writeContent(result)           → stdout 居中输出
```

### 对现有组件的改动

**tool-view.ts** — 简化：不再自己管理 write 回调，改为直接操作 OutputManager：

```typescript
class ToolView {
  constructor(private om: OutputManager) {}

  onStart(call: ToolCall, agentId: string): void {
    const args = JSON.stringify(call.arguments)
    this.om.updateToolLine(`${agentTag(agentId)} ⎿  ${call.name}(${args})`)
  }

  onFinish(call: ToolCall, result: ToolResult, agentId: string): void {
    if (result.isError) {
      this.om.updateToolLine(`${agentTag(agentId)} ⎿  ${call.name} error: ${result.content}`)
    } else {
      const summary = result.content.length + ' chars'
      this.om.updateToolLine(`${agentTag(agentId)} ⎿  ✓ ${call.name} (${summary})`)
    }
  }

  onRetry(call: ToolCall, attempt: number, maxAttempts: number, agentId: string): void {
    this.om.updateToolLine(`${agentTag(agentId)} ⎿  ↻ ${call.name} (retry ${attempt}/${maxAttempts})`)
  }
}
```

**index.ts** — 所有输出点走 OutputManager：

| 输出点 | 原来 | 改为 |
|--------|------|------|
| banner | `cons.log(renderBanner())` | `om.writeContent(renderBanner())` |
| 分隔线 | `cons.log(theme.separator(...))` | `om.writeLine(theme.separator(...))` |
| 流式 chunk | `proc.stdout.write(chunk)` | `proc.stdout.write(chunk)`（左对齐，不居中）|
| `onToolRetry` 注册 | 未使用 | 传入回调 → `toolView.onRetry()` |
| 完整结果 | `cons.log(render(result.output))` | `om.writeContent(render(result.output))` |
| 排队提示 | `cons.log(theme.queue(...))` | `om.writeLine(theme.queue(...))` |
| 错误 | `cons.error(theme.error(...))` | `om.writeLine(theme.error(...))` |

注意：
- 流式 token 保持左对齐（逐 token 到达，无法预计算居中位置；缓冲再渲染会破坏实时感）
- 分隔线 `'─'.repeat(65)` 改为 `'─'.repeat(terminalWidth)` 以对齐居中布局
- 最终结果渲染时居中

## 测试策略

1. **OutputManager 单元测试** — mock stdout/stderr，验证居中 padding、`\r` 覆盖、行清空
2. **ToolView 单元测试** — mock OutputManager，验证 updateToolLine 调用参数
3. **Spinner 不变** — 现有测试继续通过
4. **CLI 集成测试** — 验证 `runCli()` 依赖注入模式下不报错
5. **已有 227 测试全通过** — 不改坏已有逻辑

## 不变的部分

- `runAgentLoop.ts` — 不改（tool 回调链路不变）
- `Platform.ts` — 不改
- `theme.ts` — 不改颜色定义
- `renderer.ts` — 不改 markdown 渲染逻辑
- 构建配置 — 不改（不新增外部依赖）
