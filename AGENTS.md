# AGENTS.md — AI Agent Platform

## 架构阅读指南

- V1 实现者 **只看** `docs/architecture-v1.md` + `docs/v1-implementation-steps.md`
- `docs/architecture.md` 是 v4 全平台架构 — 包含 Plugin/Skill/Hook/AgentRegistry/LTM/流式等特性，**V1 全部跳过**
- V4 vs V1 差异对照表在 `architecture-v1.md §九`

## V1 实施规则

- **严格串行**：Phase 0 → 1 → ... → 7，不得跳步或并行
- **TDD 强制**：先写测试再实现，覆盖率 ≥ 80%
- **immutable 数据**：`structuredClone()` 再写入，`getContext()` 返回快照
- **错误处理**：所有工具 execute 返回 `{ content, isError: true }`，不抛未捕获异常

## 技术栈

| 配置 | 值 |
|------|-----|
| 包管理器 | pnpm workspace (`packages/*`, `packages/tools/*`, `apps/*`) |
| 模块系统 | ESM（`"type": "module"`） |
| TypeScript | `module: "NodeNext"`, `moduleResolution: "NodeNext"`, `target: "ES2022"`, `strict: true` |
| 构建 | `tsc --build`（project references）+ `node build.mjs`（esbuild 打包 CLI） |
| 测试 | vitest（`vitest.config.ts` resolve.alias 映射 `@agent-platform/*` → `packages/*/src/index.ts`） |
| 格式化 | Prettier: singleQuote, no semi, trailingComma all |
| ESLint | flat config（`eslint.config.js`），no-console（允许 logger.ts + tests/**/*.spec.ts），`@typescript-eslint/no-unused-vars` 忽略 `^_` 参数 |

## 开发命令

```sh
pnpm install          # 安装依赖
pnpm run build        # tsc --build + node build.mjs
pnpm run lint         # ESLint 零警告
pnpm run test         # vitest 全部通过 + 覆盖率 ≥ 80%
```

## 代码实现事实（已从代码验证，与架构文档可能有出入）

### 包依赖图（实际代码）

```
shared-types (零依赖)
  ├── memory-stm (依赖 shared-types)
  ├── llm-adapter (依赖 shared-types)
  ├── tools/* (依赖 shared-types)
  ├── tool-core (依赖 shared-types + memory-stm + llm-adapter)
  └── platform (依赖 shared-types + llm-adapter + tool-core + memory-stm + tools/*)
        └── apps/cli (依赖 platform)
```

### Agent Loop 关键细节

- `runAgentLoop` 将 system prompt 放入 messages 数组发送给 `llm.complete()`（不是分离参数）；`ClaudeAdapter` 内部再提取回 Anthropic `system` 参数
- 消息存储在 **loop 内部的局部 `messages` 数组**，STM 仅用于 `compact()` 释放 token 预算，不作为消息存储
- `AgentLoopConfig.contextWindow` 独立于 `agent.contextWindow`；优先使用 `config.contextWindow`
- `AgentResult.status` 四值：`'completed' | 'max_iterations_reached' | 'failed' | 'aborted'`

### ToolRegistry 内部实现

- **两个映射**：`handlers`（key=handler.id，用于 `getAllTools()`）+ `toolToHandler`（key=tool.name，用于 `execute()` 按名查找）
- 全局路径安全防线在 `execute()` 中：提取 args 中的 `path`/`filepath` 字段，`path.resolve` + `startsWith` 校验
- `ToolHandler` V1 仅 `id` + `getTools()` + `execute()`，无 `name`/`version`

### Anthropic Adapter

- 构造函数可注入 `fetchFn`（用于测试 mock）+ 独立 `model`/`maxTokens`/`temperature`（与 Agent config 分离）
- `tool_use` 角色在 Anthropic API 中映射为 `role: 'assistant'` 的 `content` 数组（含 `tool_use` block）
- `tool` 角色消息映射为 `role: 'user'`（Anthropic 的 tool_result 格式）
- 重试：429/502/503 → 最多 2 次，指数退避 1s/2s/max 5s

### Session / Agent 查找

- **无 SessionManager 类**：`Platform.createSession()` 直接返回 `{ id, agentId, projectRoot, stm }` 对象，无 Map 管理，无 mutex
- **Agent 查找硬编码**：`getAgent(id)` 用 `if (id === 'coding-agent')`，不走 Registry
- **CLI 测试模式**：`runCli()` 接受 `{ PlatformCtor?, readFileSync?, process?, console?, readline?, userConfigOverride? }` 依赖注入

### STM ShortTermMemory

- `compact()` 有 `compacted` 标志位，压缩一次后后续调用返回 0（不重复压缩）
- `maxCapacity` 参数用于 Ring Buffer 上限（0=不限制）

## 关键差异（V1 特有简化）

- **LLM Adapter**：V1 签名 `complete(messages, tools?)`（位置参数），V4 改为 `complete(options)`（对象参数）
- **ToolHandler**：V1 只有 `id` + `getTools()` + `execute()`，V4 加 `name` / `version`
- **Agent Orchestrator**：V1 Orchestrator 也是 Agent，共享 `runAgentLoop`
- **STM compact()**：V1 基于规则的角色分组摘要（非 LLM），有 `compacted` 防重复标志
- **Token 预算**：`agent.contextWindow * runtime.compressionRatio` 计算触发 compact 的阈值
- **Agent 查找**：V1 硬编码 `getAgent(id)` if/else，不使用 AgentRegistry
- **Session**：V1 进程内 `Platform.createSession()` 直接返回对象，无持久化、无 mutex

## 架构约定

- Monorepo 目录：`packages/*`（库），`apps/cli/`（CLI 入口），`tests/`（根级别 vitest 管理，分 unit/contract-tests/e2e）
- `AgentConfig`（纯 JSON 数据）与 `Agent`（含 handler 引用）分离 — 配置文件中不出现 handler
- Tool 路径安全：全局主防线在 `ToolRegistry.execute()` — 提取 `path`/`filepath` 字段做 `path.resolve` + `startsWith` 校验
- Terminal 安全：命令白名单（30+ 命令）+ shell metacharacter 注入检测（不是黑名单）
- 配置加载优先级：`~/.agent-platform/config.json` > `process.env.ANTHROPIC_API_KEY` > throw
- `build.mjs` 只用 esbuild 打包 `apps/cli/src/index.ts` → `apps/cli/dist/cli.js`（CLI 可执行入口）

## 接口不变性

以下接口是全局契约，更改视为破坏性变更：
- `ChatMessage`, `ToolCall`, `ToolResult`, `ToolDefinition`（`packages/shared-types/src/chat.ts`）
- `ChatResponse`, `TokenUsage`, `AgentResult`（`packages/shared-types/src/llm.ts`）
- `Agent`, `ToolHandler`, `ToolExecutionContext`（`packages/shared-types/src/agent.ts`）
- `PlatformConfig`（`packages/shared-types/src/config.ts`）

改接口前需确认所有消费方同步更新。
