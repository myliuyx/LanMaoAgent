# Agent 配置重构设计

## 动机

当前 Agent 定义以内联 JSON 数组形式放在 `config.json` 中，存在以下问题：

- Agent 数量增多（几十上百个）时配置文件膨胀不可维护
- `systemPrompt` 可长达数百行，不适合内联
- 无法复用公共工具集
- Agent 间无继承关系，每个 agent 需重复声明全部工具

## 架构

### 目录结构

```
~/.agent-platform/agents/
  index.json              # 启用哪些 agent（显式列表）
  orchestrator/
    agent.json            # 元信息
    system-prompt.md      # 系统提示词
  coding-agent/
    agent.json
    system-prompt.md
  stock-agent/
    agent.json
    system-prompt.md
```

子目录名 = agent ID。只有 `index.json` 中列出的 ID 才会被加载。

### `index.json`

```json
["orchestrator", "coding-agent", "stock-agent"]
```

纯字符串数组，每个元素对应一个 agent 子目录名。启动时按数组顺序加载。

### `agent.json`

```json
{
  "name": "股票查询助手",
  "description": "查询实时股票数据和历史行情",
  "tools": ["stock-api"],
  "extends": "base-coder"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 可读名称 |
| `description` | 否 | 描述，用于委派时的语义匹配 |
| `tools` | 否 | 该 agent 额外需要的工具 ID 列表 |
| `extends` | 否 | 父 agent ID，继承其 tools |

### `config.json` 改动

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

| 字段 | 说明 |
|------|------|
| `defaultTools` | 所有 agent 的基础工具集，合并到每个 agent |
| `agentsDir` | agent 目录路径，默认 `~/.agent-platform/agents` |

移除原内联 `agents` 数组（`config.json` 中不再包含）。`BUILTIN_AGENTS` 保留作为兜底。

### 工具合并规则

```
最终工具集 = defaultTools ∪ extends 继承链上的所有 tools ∪ 自身 tools
```

全部合并去重（Set 去重），不覆盖。示例：

```
defaultTools:                   [filesystem, git, terminal]
base-coder tools:               [git-log]
  → 最终:                        [filesystem, git, terminal, git-log]
stock-agent extends base-coder: + [stock-api]
  → 最终:                        [filesystem, git, terminal, git-log, stock-api]
```

继承链深度不限，循环继承应报错。

### 内置 Agent 兜底

orchestrator / coding-agent 仍然以代码内置在 `platform/src/agents.ts` 中。
每个内置 agent 增加 `tools` 字段，指定所需工具 ID。

加载逻辑（在 CLI 的 `loadAgents()` 中）：

1. 读取 `index.json`，拿到 agent ID 列表
2. 对每个 ID，查找 `agentsDir/{id}/agent.json`
3. 如果找到 → 解析并加载
4. 如果没找到 → fallback 到内置版本（`BUILTIN_AGENTS`）
5. 如果内置也没有 → 报错

这样用户可以通过创建同名子目录覆盖任意内置 agent。

### system-prompt.md 加载

先在 `agentsDir/{id}/system-prompt.md` 找。
如果文件不存在，使用内置默认 prompt（如果有）。
如果既无文件也无内置，使用空字符串。

## 数据流

```
启动
  └→ loadConfig() 读取 config.json
  └→ loadAgents() 同步读取 agentsDir：
       ├→ 校验 agentsDir 是否存在（不存在则跳过目录加载）
       ├→ 读取 index.json（不存在则跳过目录加载）
       ├→ for each agentId in index:
       │    ├→ 读取 agent.json
       │    ├→ 检测循环继承（Set 记录已访问 ID）
       │    ├→ 合并工具集（defaultTools ∪ extends链 ∪ 自身）
       │    └→ 读取 system-prompt.md（可选）
       └→ 对 index 中找不到目录的 ID → fallback 到 BUILTIN_AGENTS
  └→ 返回 AgentConfig[]（使用 CLI 内联兜底）
  └→ 传入 Platform 构造函数（保持同步）
```

**关键设计决策**：Agent 加载在 CLI 层完成（同步文件 IO），Platform 构造函数保持同步。
这避免了 Platform 构造函数变为 async 的破坏性变更。

### `~` 路径展开

`agentsDir` 支持 `~` 前缀，在加载时通过 `path.resolve(os.homedir(), ...)` 展开。

## 接口变更

### `packages/shared-types/src/config.ts`

```typescript
export interface AgentConfig {
  id: string
  name: string
  description: string
  systemPrompt: string
  tools: string[]  // 新增：绑定的工具 ID 列表
}

export interface PlatformConfig {
  llm: LlmConfig
  defaultTools?: string[]   // 新增
  agentsDir?: string        // 新增
  agents: AgentConfig[]     // 不变（仍由 CLI 传入，只是来源从内联改为目录加载）
  runtime?: RuntimeConfig
  security?: SecurityConfig
  cli?: CliConfig
}
```

注意 `agents` 字段仍然保留，类型不变。只是数据来源从内联 JSON 改为目录加载。
Platform 本身不需要感知加载细节。

### `packages/platform/src/agents.ts`

`BUILTIN_AGENTS` 保留作为兜底，每个内置 agent 增加 `tools` 字段：

```typescript
export const BUILTIN_AGENTS: AgentConfig[] = [
  {
    id: 'orchestrator',
    name: '编排者',
    description: '负责分解任务、委派专业 Agent、汇总结果',
    systemPrompt: '你是一个多智能体编排系统...',
    tools: ['delegate_to_agent'],
  },
  {
    id: 'coding-agent',
    name: '编码专家',
    description: '负责编写、修改、调试代码',
    systemPrompt: '你是资深开发者...',
    tools: ['filesystem', 'git', 'terminal'],
  },
]
```

### `packages/platform/src/Platform.ts` — tools → handler 映射

Platform 构造函数中维护一个 `handlerMap: Map<string, ToolHandler>`，注册 handler 时建立映射：

```typescript
private handlerMap = new Map<string, ToolHandler>()

// 注册时：
this.handlerMap.set(fsHandler.id, fsHandler)
this.handlerMap.set(gitHandler.id, gitHandler)
// ...

// buildAgent 时按 tools 列表筛选 handler：
function resolveHandlers(toolIds: string[], handlerMap: Map<string, ToolHandler>): ToolHandler[] {
  return toolIds.map(id => handlerMap.get(id)).filter(Boolean) as ToolHandler[]
}
```

`buildAgent()` 签名不变，但调用时只传入 agent 所需的 handler。

### `apps/cli/src/index.ts`

新增 `loadAgents()` 函数，负责：
1. 读取 `agentsDir/index.json`
2. 按 ID 读取每个 `agent.json` + `system-prompt.md`
3. 合并工具集（defaultTools + extends 链）
4. 对找不到目录的 ID，fallback 到内置版本
5. 如果 agentsDir 不存在或 index.json 不存在，使用内置兜底

`loadConfig()` 不再包含 agents 逻辑。

## 向后兼容

- 如果 `agentsDir` 不存在或 `index.json` 不存在，fallback 到内置 agent（orchestrator + coding-agent）
- 内置兜底确保现有功能不中断

## 未涉及的范围

- Agent 版本管理
- Agent 热加载 / 动态注册
- 跨项目共享 agent
- `description` 用于语义匹配的具体实现

## 实施步骤

1. `shared-types/src/config.ts` — `AgentConfig` 增加 `tools?: string[]`；`PlatformConfig` 增加 `defaultTools?: string[]`、`agentsDir?: string`
2. `platform/src/agents.ts` — 内置 agent 增加 `tools` 字段
3. `apps/cli/src/index.ts` — 新增 `loadAgents()` 函数：读取 index.json、解析 agent.json、合并工具集、检测循环继承、fallback 内置兜底
4. `platform/src/Platform.ts` — 构造函数增加 `handlerMap`；`buildAgent()` 调用时按 agent.tools 筛选 handler；fallback 逻辑：如果未配置 agentsDir 或 index.json 不存在，使用 BUILTIN_AGENTS
5. `config.example.json` + `~/.agent-platform/config.json` — 更新为新的配置结构
6. 测试

### 测试策略

- `loadAgents()` 单元测试：
  - 正常加载 index.json + agent.json
  - extends 继承合并
  - 循环继承报错
  - directory 不存在时 fallback
  - system-prompt.md 存在/不存在
- `Platform` 构造测试：
  - handlerMap 映射正确
  - agent tools 筛选 handler 正确
  - defaultTools 合并正确
- cli.spec.ts 更新：不再模拟内联 agents，改为模拟 agentsDir
