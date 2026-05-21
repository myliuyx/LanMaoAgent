# 多智能体编程工作流 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 platform 添加 planner/reviewer/tester 三个 Agent，形成完整的 coding workflow

**Architecture:** 纯配置变更——在 `BUILTIN_AGENTS` 中定义新 Agent 及其 system prompt/tools，在用户配置目录创建 agent.json。所有 agent 共享已有 ToolHandler，行为差异由 system prompt 和 tool 列表控制。

**Tech Stack:** TypeScript, monorepo packages, 用户目录配置

---

### 前置状态

以下代码/配置已经在设计确认阶段完成，无需再执行：

- `packages/platform/src/agents.ts` — BUILTIN_AGENTS 已添加 planner/reviewer/tester，orchestrator prompt 已升级
- `~/.agent-platform/agents/planner/agent.json` — 已创建，tools: [filesystem]
- `~/.agent-platform/agents/reviewer/agent.json` — 已创建，tools: [filesystem, git, terminal]
- `~/.agent-platform/agents/tester/agent.json` — 已创建，tools: [filesystem, git, terminal]
- `~/.agent-platform/agents/index.json` — 已更新为 5 个 agent
- `tests/unit/platform/agents.spec.ts` — 已更新为 5 个 agent 校验

### Task 1: 构建验证

- [ ] **Step 1: 运行 tsc --build 确保编译通过**

```bash
corepack pnpm run build
```
Expected: 退出码 0，无错误输出

- [ ] **Step 2: 运行 ESLint 确保零警告**

```bash
corepack pnpm run lint
```
Expected: 退出码 0，无输出

- [ ] **Step 3: 运行 vitest 确保 179 tests 全部通过**

```bash
corepack pnpm run test
```
Expected: 22 files passed, 179 tests passed

### Task 2: 端到端冒烟测试

- [ ] **Step 1: 启动 CLI，确认 orchestrator 能识别所有 Agent**

启动 CLI 后用简单请求："列出所有可用的 Agent"
预期：orchestrator 应该能看到 planning-coding-reviewing-testing 体系
（不要求实际委派，只确认系统启动正常且 agent 注册正确）

### Task 3: 可选 — 集成测试（已验证核心功能后）

**文件中标记的两个未来任务暂不实现：**
1. orchestrator → planner → coding-agent 完整链路集成测试
2. reviewer terminal 安全约束验证

原因：这两个需要 mock LLM adapter 构造真实委派场景，工程量大且已有单元测试覆盖 Agent 定义的正确性。建议 V2 再补充。
