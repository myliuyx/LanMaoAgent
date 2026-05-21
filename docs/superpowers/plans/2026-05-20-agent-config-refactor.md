# Agent 配置重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Agent 定义从内联 JSON 迁移到基于目录的独立文件，支持工具集继承和系统提示词分离。

**Architecture:** Agent 元数据从 `~/.agent-platform/agents/{id}/agent.json` 加载，system prompt 放在同目录的 `system-prompt.md`。CLI 层负责同步加载并解析继承链，然后以 `AgentConfig[]` 传给 Platform 构造函数（保持同步不变）。Platform 维护 `handlerMap` 按 `tools: string[]` 筛选 handler。

**Tech Stack:** TypeScript, Node.js fs (同步), vitest

---

### Task 1: 配置类型扩展

**Files:**
- Modify: `packages/shared-types/src/config.ts:1-23`

- [ ] **Step 1: 给 `AgentConfig` 加 `tools` 和 `extends` 字段**

```typescript
export interface AgentConfig {
  id: string
  name: string
  description: string
  systemPrompt: string
  tools?: string[]
  extends?: string
}
```

- [ ] **Step 2: 给 `PlatformConfig` 加 `defaultTools` 和 `agentsDir`**

```typescript
export interface PlatformConfig {
  llm: LlmConfig
  agents: AgentConfig[]
  defaultTools?: string[]
  agentsDir?: string
  runtime?: RuntimeConfig
  security?: SecurityConfig
  cli?: CliConfig
}
```

- [ ] **Step 3: 新增 `DEFAULT_AGENTS_DIR` 常量**

```typescript
export const DEFAULT_AGENTS_DIR = '~/.agent-platform/agents'
export const DEFAULT_TOOLS: string[] = ['filesystem', 'git', 'terminal']
```

- [ ] **Step 4: 运行测试验证类型变更无破坏**

Run: `cd /home/shaomai/agent_work/project_agent && node_modules/.bin/vitest run tests/unit/shared-types/config.spec.ts`
Expected: PASS

---

### Task 2: 内置 Agent 加 tools

**Files:**
- Modify: `packages/platform/src/agents.ts`

- [ ] **Step 1: 读取当前 agents.ts**

Run the read tool to show current file content:
`packages/platform/src/agents.ts`

- [ ] **Step 2: 给每个内置 agent 增加 `tools` 字段**

Orchestrator 的 tools: `['delegate_to_agent']`
Coding-agent 的 tools: `['filesystem', 'git', 'terminal']`

```typescript
export const BUILTIN_AGENTS: AgentConfig[] = [
  {
    id: 'orchestrator',
    name: '编排者',
    description: '负责分解任务、委派专业 Agent、汇总结果',
    systemPrompt: `...（不做变更）`,
    tools: ['delegate_to_agent'],
  },
  {
    id: 'coding-agent',
    name: '编码专家',
    description: '负责编写、修改、调试代码',
    systemPrompt: `...（不做变更）`,
    tools: ['filesystem', 'git', 'terminal'],
  },
]
```

- [ ] **Step 3: 运行测试**

Run: `node_modules/.bin/vitest run tests/unit/platform/`
Expected: PASS

---

### Task 3: CLI 层 loadAgents() 函数

**Files:**
- Modify: `apps/cli/src/index.ts:14-55`

- [ ] **Step 1: 导入新依赖**

在文件顶部增加 import:

```typescript
import os from 'node:os'
import { DEFAULT_TOOLS, DEFAULT_AGENTS_DIR } from '@agent-platform/shared-types'
```

- [ ] **Step 2: 实现 loadAgents() 函数**

```typescript
function loadAgents(
  agentsDir: string,
  defaultTools: string[],
  readFileSync: typeof fs.readFileSync,
): AgentConfig[] {
  const resolvedDir = agentsDir.startsWith('~')
    ? path.join(os.homedir(), agentsDir.slice(1))
    : agentsDir

  // agentsDir 不存在或 index.json 不存在 → 使用内置兜底
  let index: string[]
  try {
    fs.statSync(resolvedDir)
    index = JSON.parse(readFileSync(path.join(resolvedDir, 'index.json'), 'utf-8'))
  } catch {
    return BUILTIN_AGENTS
  }

  const builtinMap = new Map(BUILTIN_AGENTS.map((a) => [a.id, a]))
  const loaded = new Map<string, AgentConfig>()
  const result: AgentConfig[] = []

  function resolveOne(id: string, visited: Set<string>): AgentConfig {
    if (visited.has(id)) {
      throw new Error(`Circular extends detected for agent "${id}"`)
    }

    const cached = loaded.get(id)
    if (cached) return cached

    // 优先从文件加载，其次内置兜底
    const agentPath = path.join(resolvedDir, id, 'agent.json')
    let cfg: Partial<AgentConfig> & { extends?: string; tools?: string[] }
    try {
      cfg = JSON.parse(readFileSync(agentPath, 'utf-8'))
    } catch {
      const builtin = builtinMap.get(id)
      if (!builtin) throw new Error(`Agent "${id}" not found in agents dir or built-in`)
      loaded.set(id, builtin)
      return builtin
    }

    visited.add(id)
    const agent: AgentConfig = {
      id,
      name: cfg.name ?? id,
      description: cfg.description ?? '',
      systemPrompt: '',
      tools: cfg.tools,
      extends: cfg.extends,
    }

    // 解析继承链
    let baseTools: string[]
    if (agent.extends) {
      const parent = resolveOne(agent.extends, visited)
      baseTools = [...new Set([...(parent.tools ?? defaultTools), ...(agent.tools ?? [])])]
    } else {
      baseTools = [...new Set([...defaultTools, ...(agent.tools ?? [])])]
    }
    agent.tools = baseTools

    // 读取 system-prompt.md
    const promptPath = path.join(resolvedDir, id, 'system-prompt.md')
    try {
      agent.systemPrompt = readFileSync(promptPath, 'utf-8')
    } catch {
      const builtin = builtinMap.get(id)
      if (builtin) agent.systemPrompt = builtin.systemPrompt
    }

    loaded.set(id, agent)
    return agent
  }

  for (const id of index) {
    result.push(resolveOne(id, new Set()))
  }

  return result
}
```

- [ ] **Step 3: 更新 loadConfig() 返回 PlatformConfig，其中 agents 来自 loadAgents()**

```typescript
function loadConfig(
  readFileSync: typeof fs.readFileSync,
  proc: NodeJS.Process,
  userConfigOverride?: Partial<PlatformConfig>,
): PlatformConfig {
  let userConfig: Partial<PlatformConfig> = {}
  try {
    const CONFIG_FILE = path.join(os.homedir(), '.agent-platform', 'config.json')
    userConfig = JSON.parse(readFileSync(CONFIG_FILE, 'utf-8'))
  } catch {
    // config file missing or invalid — use defaults
  }

  if (userConfigOverride) {
    userConfig = { ...userConfig, ...userConfigOverride }
  }

  const envApiKey = proc.env.ANTHROPIC_API_KEY
  const llmApiKey = userConfig.llm?.apiKey ?? envApiKey

  const agentsDir = userConfig.agentsDir ?? DEFAULT_AGENTS_DIR
  const defaultTools = userConfig.defaultTools ?? DEFAULT_TOOLS

  const agents = loadAgents(agentsDir, defaultTools, readFileSync)

  return {
    llm: { ...DEFAULT_LLM, provider: 'anthropic', ...userConfig.llm, apiKey: llmApiKey },
    agents,
    defaultTools,
    agentsDir,
    runtime: { ...DEFAULT_CONFIG.runtime, ...userConfig.runtime },
    security: { ...DEFAULT_CONFIG.security, ...userConfig.security },
    cli: {
      prompt: userConfig.cli?.prompt ?? DEFAULT_CONFIG.cli?.prompt ?? 'Ask me anything: ',
    },
  }
}
```

- [ ] **Step 4: 运行测试验证 CLI 构建**

Run: `node_modules/.bin/tsc --build && node build.mjs`
Expected: 无错误

---

### Task 4: Platform handlerMap + agent 构建

**Files:**
- Modify: `packages/platform/src/Platform.ts:24-85`

- [ ] **Step 1: 添加 handlerMap 和 agent 批量构建**

修改 Platform 类：

```typescript
export class Platform {
  private llm: LLMAdapter
  private registry: ToolRegistry
  private orchestratorAgent: Agent
  private config: PlatformConfig
  private agentsCache = new Map<string, Agent>()
  private handlerMap = new Map<string, ToolHandler>()

  constructor(config: PlatformConfig) {
    this.config = { ...DEFAULT_CONFIG, ...config, llm: config.llm }

    const provider = this.config.llm.provider ?? 'anthropic'
    if (provider === 'openai') {
      this.llm = new OpenAIAdapter(this.config.llm)
    } else {
      if (!this.config.llm.apiKey) {
        throw new Error('llm.apiKey required for anthropic provider (set ANTHROPIC_API_KEY env var or config file)')
      }
      this.llm = new ClaudeAdapter(this.config.llm)
    }

    this.registry = new ToolRegistry()

    const fsHandler = new FilesystemHandler()
    const gitHandler = new GitHandler()
    const termWhitelist = this.config.security?.terminalWhitelist ?? []
    const termHandler = new TerminalHandler(termWhitelist)

    for (const h of [fsHandler, gitHandler, termHandler]) {
      this.registry.register(h)
      this.handlerMap.set(h.id, h)
    }

    const delegateHandler = new DelegateToAgentHandler(
      { get: (id: string) => this.getAgent(id) },
      this.llm,
      this.registry,
      this.config.runtime?.compressionRatio,
    )
    this.registry.register(delegateHandler)
    this.handlerMap.set(delegateHandler.id, delegateHandler)

    // 按 config.agents 批量构建 Agent
    for (const agentConfig of config.agents) {
      const handlers = (agentConfig.tools ?? [])
        .map((id) => this.handlerMap.get(id))
        .filter(Boolean) as ToolHandler[]
      const agent = buildAgent(agentConfig, handlers, {
        contextWindow: this.config.runtime?.contextWindow,
      })
      this.agentsCache.set(agentConfig.id, agent)
      if (agentConfig.id === 'orchestrator') {
        this.orchestratorAgent = agent
      }
    }
  }
```

- [ ] **Step 2: 简化 getAgent() — 直接从缓存查找**

```typescript
private getAgent(id: string): Agent | undefined {
  return this.agentsCache.get(id)
}
```

- [ ] **Step 3: 运行测试**

Run: `node_modules/.bin/tsc --build && node_modules/.bin/vitest run`
Expected: 160 PASS（平台相关测试涉及 mock，需要确认不会因为 handlerMap 断掉）

---

### Task 5: CLI 集成收尾

**Files:**
- Modify: `apps/cli/src/index.ts:57-130`

- [ ] **Step 1: 确认 runCli() 中不再有 `userConfigOverride?.agents ?? BUILTIN_AGENTS` 逻辑**

现在的 `loadConfig()` 已经返回完整的 PlatformConfig，包括已解析的 `agents`。如果 `userConfigOverride` 包含 `agents`，在 `loadConfig` 中会合并。PlatformConfig 中的 `agents` 永远是已经加载解析完成的 AgentConfig[]。

- [ ] **Step 2: 运行完整构建 + 测试**

Run: `node_modules/.bin/tsc --build && node build.mjs && node_modules/.bin/vitest run`
Expected: 全部通过

---

### Task 6: 配置文件和示例 agent

- [ ] **Step 1: 更新 `config.example.json`**

```json
{
  "llm": {
    "provider": "openai",
    "apiKey": "__YOUR_API_KEY_HERE__",
    "baseUrl": "http://192.168.3.21:8080",
    "timeoutSec": 120,
    "stream": true
  },
  "defaultTools": ["filesystem", "git", "terminal"],
  "agentsDir": "/home/shaomai/.agent-platform/agents",
  "runtime": {
    "maxIterations": 20,
    "stmThreshold": 50,
    "compressionRatio": 0.85,
    "contextWindow": 260000
  },
  "security": {
    "allowedPaths": [],
    "terminalWhitelist": []
  },
  "cli": {
    "prompt": "Ask me anything: "
  }
}
```

- [ ] **Step 2: 更新 `~/.agent-platform/config.json`**（同上）

- [ ] **Step 3: 创建 `~/.agent-platform/agents/` 目录和 index.json**

```bash
mkdir -p ~/.agent-platform/agents
cat > ~/.agent-platform/agents/index.json << 'EOF'
["orchestrator", "coding-agent"]
EOF
```

- [ ] **Step 4: 创建 orchestrator 和 coding-agent 目录+文件**

orchestrator:
```bash
mkdir -p ~/.agent-platform/agents/orchestrator
cat > ~/.agent-platform/agents/orchestrator/agent.json << 'EOF'
{
  "name": "编排者",
  "description": "负责分解任务、委派专业 Agent、汇总结果",
  "tools": ["delegate_to_agent"]
}
EOF
cat > ~/.agent-platform/agents/orchestrator/system-prompt.md << 'PROMPT'
你是一个多智能体编排系统。你不直接写代码。你的职责：分解任务，使用 delegate_to_agent 委派给专业 Agent，收集结果后返回给用户。
PROMPT
```

coding-agent:
```bash
mkdir -p ~/.agent-platform/agents/coding-agent
cat > ~/.agent-platform/agents/coding-agent/agent.json << 'EOF'
{
  "name": "编码专家",
  "description": "负责编写、修改、调试代码",
  "tools": ["filesystem", "git", "terminal"]
}
EOF
cat > ~/.agent-platform/agents/coding-agent/system-prompt.md << 'PROMPT'
你是资深开发者。你的职责：编写、修改、调试代码。使用 filesystem 工具读写文件，使用 git 工具查看变更，使用 terminal 执行命令。
PROMPT
```

- [ ] **Step 5: 运行完整测试**

Run: `node_modules/.bin/vitest run`
Expected: 160 PASS

---

### Task 7: 测试

**Files:**
- Modify: `tests/unit/platform/cli.spec.ts`
- Create: `tests/unit/agents/index.spec.ts`（独立的 agent 加载测试）

- [ ] **Step 1: 创建 agents 加载单元测试**

新建 `tests/unit/agents/index.spec.ts`，通过 `vi.mock('node:fs')` 模拟文件系统：

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AgentConfig } from '@agent-platform/shared-types'
import { BUILTIN_AGENTS } from '@agent-platform/platform'

const mockReadFileSync = vi.fn()
vi.mock('node:fs', () => ({
  default: { readFileSync: mockReadFileSync, statSync: vi.fn() },
  readFileSync: mockReadFileSync,
  statSync: vi.fn(),
}))

describe('agent loading from agentsDir', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('falls back to built-in agents when agentsDir is missing', async () => {
    const { loadConfig } = await import('../../../apps/cli/src/index.js')

    // mocking...
  })
})
```

- [ ] **Step 2: 更新 cli.spec.ts 中的数据流测试**

对 `config.json apiKey takes precedence over env var` 测试，更新验证 PlatformCtor 收到的 agents 是内置兜底（因为 mock readFileSync 不会返回 agentsDir 相关数据）：

```typescript
it('config.json apiKey takes precedence over env var', async () => {
  const { runCli } = await import('../../../apps/cli/src/index.ts')

  const mockReadFileSync = vi.fn().mockReturnValue(
    JSON.stringify({ llm: { apiKey: 'config-key' } }),
  )

  runCli({
    readFileSync: mockReadFileSync as unknown as typeof import('fs').readFileSyncSync,
    process: {
      env: { ANTHROPIC_API_KEY: 'env-key' },
      exit: exitMock,
      on: onMock,
      stdout: { write: vi.fn(), isTTY: true },
      stdin: { on: vi.fn(), setRawMode: vi.fn() },
      argv: ['node', 'test'],
    } as unknown as NodeJS.Process,
    console: { log: logMock, error: errorMock } as unknown as Console,
    PlatformCtor: platformCtorMock.mockImplementation(function MockPlatform() {
      return { run: runMock }
    }),
    readline: {
      createInterface: vi.fn().mockReturnValue({
        on: vi.fn(),
        close: vi.fn(),
        prompt: vi.fn(),
        write: vi.fn(),
      }),
    } as unknown as typeof import('node:readline'),
  })

  expect(platformCtorMock).toHaveBeenCalled()
  const config = platformCtorMock.mock.calls[0][0]
  expect(config.llm.apiKey).toBe('config-key')
  // agents 应该是内置兜底（不为空）
  expect(config.agents.length).toBeGreaterThan(0)
})
```

- [ ] **Step 3: 为 handlerMap 添加 platform 测试**

验证 Platform 构造后 handlerMap 包含所有 handler：

需要在 Platform 的测试中或单独的 handlerMap 测试中：

```typescript
it('handlerMap contains all registered handlers', () => {
  const platform = new Platform({
    llm: { provider: 'anthropic', apiKey: 'test-key' },
    agents: BUILTIN_AGENTS,
  })
  // handlerMap 是私有字段，需要通过行为测试验证
  // 例如：orchestrator 应该只有 delegate_to_agent 一个 handler
  // coding-agent 应该有 filesystem, git, terminal 三个 handler
})
```

- [ ] **Step 4: 运行全部测试**

Run: `node_modules/.bin/tsc --build && node_modules/.bin/vitest run`
Expected: 全部通过

---

### Self-Review Checklist

- [ ] 所有 `AgentConfig` 引用处都已处理 `tools` 可选字段
- [ ] `DEFAULT_TOOLS` 和 `DEFAULT_AGENTS_DIR` 引入后无循环依赖
- [ ] 当 `agentsDir`/`index.json` 不存在时，`loadAgents` 返回 `BUILTIN_AGENTS`（不是空数组）
- [ ] `loadAgents` 处理了 `extends` 循环引用（visited Set）
- [ ] `Platform` 构造过程没有变为 async
- [ ] `config.example.json` 和用户的 config 都更新了
- [ ] 现有测试全部通过
