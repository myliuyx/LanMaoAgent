# Terminal UI 改造设计

## 概述

将当前纯文本 CLI 改造为 Claude Code 风格的彩色终端界面，包括：彩色提示符、Markdown 渲染、代码语法高亮、工具调用可视化、加载动画、错误着色。

## 范围

改动涉及：
- `apps/cli/src/` — 新增 `ui/` 目录 + 更新 `index.ts`
- `packages/tool-core/src/runAgentLoop.ts` — 新增 2 个可选回调参数
- `packages/platform/src/Platform.ts` — 透传 2 个回调参数

不涉及核心逻辑改动（回调仅用于 UI 展示，不影响 Agent Loop 行为）。不涉及平台层重构。

## 新增依赖

| 包 | 体积 | 用途 |
|---|---|---|
| `picocolors` | ~1KB | 终端颜色 |
| `marked` | ~30KB | Markdown 解析 |
| `cli-highlight` | ~50KB | 代码语法高亮 |
| `ora` | ~15KB | 加载动画 |

打包增量约 ~100KB（当前 `cli.js` 约 50KB）。

## 新增文件

```
apps/cli/src/
  ui/theme.ts       — 颜色常量
  ui/renderer.ts    — Markdown → ANSI 渲染器
  ui/spinner.ts     — Spinner 管理器
  ui/tool-view.ts   — 工具调用可视化
  index.ts          — 更新主循环
```

## 组件设计

### 1. theme.ts — 颜色常量

```ts
// 全终端统一调色板
export const theme = {
  prompt:    magenta,     // 提示符 > 前缀
  heading1:  bold + yellow,    // # 标题
  heading2:  bold + cyan,      // ## 子标题
  bold:      bold,
  inlineCode: bgCyan + white,  // `行内代码`
  codeBlock:  dim,             // 代码块主体
  blockquote: dim + italic,    // > 引用
  link:      blue + underline, // [text](url)
  filePath:  cyan + underline, // src/file.ts:10
  toolRunning: dim,            // 正在执行的工具
  toolDone:  green,            // 已完成的工具
  toolError: red,              // 出错的工具
  error:     red + bold,       // 错误消息
  queue:     dim + yellow,     // 排队提示
  cancel:    dim,              // 取消提示
  separator: dim,              // 分隔线 ---
}
```

### 2. renderer.ts — Markdown → ANSI

职责：将完整 Markdown 文本转换为带 ANSI 转义序列的终端输出。

内部流程：
1. `marked.lexer(text)` — 解析为 token 数组
2. 遍历 token 数组，映射为 ANSI 字符串
3. 代码块 (`code` token) → `cli-highlight` 语法着色 + 灰色框线

边界情况：
- 空文本 → 原样返回
- 纯文本（无 Markdown）→ 原样返回
- 嵌套格式（`**code`）→ 先处理行内代码，再处理加粗

### 3. spinner.ts — Spinner 管理器

基于 `ora` 封装。

```
spinner = new Spinner()
spinner.start('思考中...')     // 显示旋转动画
spinner.setText('读取文件...') // 更新文案
spinner.stop()                // 清除 spinner
```

保证：
- `start()` 后再 `start()` → 自动先 stop 再 start
- `stop()` 后再 `start()` → OK
- 与 tool-view 输出不冲突（tool-view 写入前先 stop spinner，写入后重启）

### 4. tool-view.ts — 工具调用可视化

通过 `Platform.run()` 的 `onToolStart`/`onToolFinish` 回调接入。

调用时序：
```
LLM 请求工具 A → [tool-view] 显示   ⎿  tool_A(args)  (dim)
工具 A 执行完毕 → [tool-view] 更新   ⎿  tool_A 返回 (N 行)  (green)
LLM 请求工具 B → [tool-view] 显示   ⎿  tool_B(args)  (dim)
工具 B 执行完毕 → [tool-view] 更新   ⎿  tool_B 返回 (N 行)  (green)
全部工具完成    → [tool-view] 输出 --- 分隔线
LLM 开始生成回复 → [tool-view] 不介入
```

### 5. index.ts — 主要改动

| 改动 | 说明 |
|---|---|
| `readline.createInterface({ prompt })` | 替换为 `theme.prompt('> ')` + 保留原提示文案 |
| 流式输出 | 逐 chunk 写入 `process.stdout` — 保持纯文本，不做实时 Markdown 渲染 |
| 完整输出 | 调用 `renderer.render(text)` 再 `console.log` |
| 错误输出 | `console.error(theme.error(msg))` |
| 工具调用 | `Platform.run()` 新参数 `onToolStart`/`onToolFinish` → CLI 传入回调 → `tool-view.ts` |
| LLM 等待 | spinner.start('思考中...') / spinner.stop() |
| 排队 | 彩色排队提示 + ESC 取消 |
| 退出 | spinner.stop() + 清理信息 |

## 工具调用回调链路

需要在两个层面新增透传：

### runAgentLoop.ts（最小改动）

```ts
// AgentLoopConfig 新增
onToolStart?: (call: ToolCall) => void
onToolFinish?: (call: ToolCall, result: { content: string; isError: boolean }) => void

// 第 84 行前后
onToolStart?.(call)
const result = await config.registry.execute(call, config.ctx)
onToolFinish?.(call, result)
```

### Platform.run()（透传）

```ts
async run(
  request: string,
  signal?: AbortSignal,
  onChunk?: (text: string) => void,
  onToolStart?: (call: ToolCall) => void,
  onToolFinish?: (call: ToolCall, result: { content: string; isError: boolean }) => void,
): Promise<AgentResult> {
  // 传给 runAgentLoop
}
```

CLI 端的 `index.ts` 传入 `onToolStart` / `onToolFinish` 回调 → `tool-view.ts`。

## 非 TTY / 管道降级

- `picocolors` 自动检测 `isColorSupported`，非 TTY 时所有颜色输出变为纯文本
- `ora` 同理，非 TTY 时 spinner 自动隐藏
- 颜色不会泄漏到重定向输出（`node cli.js > output.txt` 无乱码）
- 测试模式下 - 通过 `process.stdout.isTTY` mock 验证降级行为

## 不变的部分

- 输入处理逻辑（readline、keypress、队列）— 不改
- 工具执行的业务逻辑（ToolRegistry、权限校验）— 不改
- 测试模式（依赖注入 `runCli({ process?, console?, ... })`）— 颜色在无 TTY 时自动降级
- 构建配置（esbuild `external: []`，新依赖会打包进去）
- 不影响已有测试（新增的都是可选回调）

## 测试策略

1. `renderer.render()` 单元测试：输入 Markdown → 验证输出包含预期 ANSI 序列；输入纯文本 → 验证不变
2. `spinner` 链式调用测试：`start/setText/stop` 不抛异常
3. `tool-view` 格式测试：mock 回调数据 → 验证输出格式
4. 非 TTY 降级测试：mock `process.stdout.isTTY = false` → 验证输出无 ANSI
5. 已有测试全过：`pnpm run test` 确认不改坏已有逻辑

## 不包含（V1 范围外）

- 交互式多选列表（`clack/prompts` 风格）
- 文件 diff 着色输出
- 终端分屏 / 面板布局
