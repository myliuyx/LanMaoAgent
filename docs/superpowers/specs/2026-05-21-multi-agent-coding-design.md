# 多智能体编程工作流设计

## 概述

将现有的 2-Agent 系统（orchestrator + coding-agent）扩展为 5-Agent 系统，增加 plan → code → review → test 的完整编程工作流。

## 现有架构

- 平台已有 `delegate_to_agent` 委派机制，orchestrator 可以动态调用子 Agent
- 子 Agent 运行独立的 `runAgentLoop`
- Agent 通过 `AgentConfig`（纯数据）+ `BUILTIN_AGENTS` 定义，用户可通过 `~/.agent-platform/agents/` 覆盖

## Agent 定义

### Orchestrator（升级）

- **id**: `orchestrator`
- **tools**: `[delegate_to_agent]`
- **职责**: 分析用户请求，按工作流模板委派子 Agent，汇总结果
- **prompt 变化**: 增加工作流模板指引、上下文传递规则、错误恢复策略

### Coding Agent（不变）

- **id**: `coding-agent`
- **tools**: `[filesystem, git, terminal]`
- **职责**: 编写、修改、调试代码

### Planner（新增）

- **id**: `planner`
- **tools**: `[filesystem]`
- **职责**: 编码前分析需求、阅读代码、产出 `.plan.md` 方案
- **限制**: 禁止 `edit_file` 修改代码，禁止 `terminal`/`git`

### Reviewer（新增）

- **id**: `reviewer`
- **tools**: `[filesystem, git, terminal]`
- **职责**: 审查代码变更，运行 lint/typecheck，输出审查报告
- **限制**: 禁止 `git push/commit/reset`、`rm`、`mv` 等写操作

### Tester（新增）

- **id**: `tester`
- **tools**: `[filesystem, git, terminal]`
- **职责**: 编写/更新测试，运行 `pnpm run test`，确保全部通过

## 协作流程

```
用户请求
    │
    ▼
Orchestrator (分析请求，选择工作流)
    │
    ├─ 新功能: planner → coding-agent → reviewer → tester
    ├─ 修复:   coding-agent → reviewer → (tester)
    ├─ 重构:   coding-agent → reviewer
    ├─ 仅审查: reviewer
    └─ 仅测试: tester
```

关键设计点：
- 子 Agent 依赖关系通过 orchestrator 串行调度，非 Agent 间直连
- 前一个 Agent 的输出文件（如 `.plan.md`）作为后一个 Agent 的输入上下文
- orchestrator 负责传递上下文：`"review the code changes made by coding-agent in the previous step"`
- orchestrator 在子 Agent 失败时可重试或切换方案

## 安全约束

Agent 的行为约束由两层保障：

| 层次 | 机制 | 说明 |
|---|---|---|
| **Prompt 层** | System Prompt 指令 | "禁止使用 edit_file"、"禁止 git push/commit" |
| **Terminal 层** | 命令白名单 | 全局白名单，对 Agent 无区分 |

V1 不引入 per-agent 权限系统，行为约束依赖 system prompt。

新增 Agent 的 terminal 安全由 orchestrator 的委派决策兜底：只有必要时才委派 terminal 给 reviewer/tester；若 reviewer 滥用 terminal，属于 prompt 层约束失败，V2 可考虑增加命令级权限控制。

## 配置变更

### 代码

- `packages/platform/src/agents.ts`: `BUILTIN_AGENTS` 增加 3 条，更新 orchestrator prompt

### 用户配置

```
~/.agent-platform/agents/
├── index.json              # ["orchestrator", "coding-agent", "planner", "reviewer", "tester"]
├── orchestrator/agent.json
├── coding-agent/agent.json
├── planner/agent.json
├── reviewer/agent.json
└── tester/agent.json
```

每个 agent.json 只定义 `name`, `description`, `tools`，system prompt 由 BUILTIN_AGENTS 提供。

## 系统 Prompt 设计原则

- 每个 Agent 的 prompt 包含：角色定义、工作流程、检查清单、限制规则
- 限制规则使用"禁止"句式，避免歧义
- Orchestrator 的 prompt 包含工作流模板而非硬编码逻辑，利用 LLM 的动态推理能力

## 测试策略

- `BUILTIN_AGENTS` 长度验证（从 2 变 5）
- 各 Agent 的 `tools` 验证
- `buildAgent` 对新增 Agent 的构建验证
- 集成测试：orchestrator → planner → coding-agent 完整链路（未实现，标记为后续）
- reviewer terminal 安全约束验证（未实现，标记为后续）
