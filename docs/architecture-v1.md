# AI Agent Platform — V1 架构设计 (编码智能体 MVP)

> **核心目标：** 一个能实际帮用户写代码的 Coding Agent。最小可工作集合，不碰一行不必要的代码。
> **演进原则：** 先跑通，再优化。V1 验证核心架构，V2+ 扩展生态。

---

## 一、V1 范围定义

### 包含 (Shipped in V1)

| 组件 | 说明 |
|------|------|
| **LLM Adapter** | 仅 Anthropic Claude（后续加 OpenAI/Google） |
| **Tool Registry** | 即插即用工具协议 + 3 个基础工具：filesystem, git, terminal |
| **Agent Loop** | 驱动 Agent 执行的通用循环（LLM ↔ Tool 迭代） |
| **Orchestrator Agent** | 接收用户请求、委派 Coding Agent、返回结果 |
| **Coding Agent** | 实际执行编码任务的 Agent |
| **Short-Term Memory (STM)** | Ring Buffer，自动压缩旧消息释放上下文空间 |
| **Session Manager** | 单进程内会话管理（Map + async mutex 覆盖并发写） |

### 推迟到 Phase 2+

| 推迟项 | 原因 |
|--------|------|
| Plugin System / Hook Bus | V1 不需要第三方扩展，官方功能足够 |
| Skill System (模板引擎) | V1 Agent 的系统提示词硬编码即可 |
| Agent Registry + Recommend | V1 只有两个 Agent（Orchestrator + Coding），无需推荐算法 |
| Long-Term Memory (LTM) / Vector Store | V1 不需要跨会话记忆，STM 足够 |
| Rate Limiter / Quota Manager | LLM API 费用风险可控，V2 再加 |
| Circuit Breaker / Fallback Chain | V1 只用 Claude，无降级需求 |
| Web API / Dashboard | V1 只做 CLI |
| Multi-user / RBAC | V1 单用户本地使用 |

---

## 二、架构总览 (V1)

```
┌─────────────────────────────────────────────────────┐
│                    CLI Entry                         │
│                  (npm install -g)                    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  User Request                                        │
│       │                                              │
│       ▼                                              │
│  ┌───────────────────┐                               │
│  │ Orchestrator Agent│  ◄── v4: Orchestrator 也是Agent │
│  │                   │                               │
│  │ 职责:              │                               │
│  │ • 分解任务         │                               │
│  │ • 委派 Coding Agent│                               │
│  │ • 汇总返回结果     │                               │
│  └────────┬──────────┘                               │
│           │                                          │
│           ▼                                          │
│  ┌─────────────────────┐                             │
│  │   Coding Agent       │ ◄── 实际执行编码任务的Agent │
│  │                     │                             │
│  │ 系统提示词:          │                             │
│  │ "你是资深开发者..."  │                             │
│  └────────┬────────────┘                             │
│           │                                          │
│    ┌──────┼──────┐                                   │
│    ▼      ▼      ▼                                   │
│ filesystem git  terminal                              │
│                                                    │
│  共享基础设施:                                      │
│  ├── LLM Adapter (Anthropic)                       │
│  ├── Tool Registry                                 │
│  ├── Agent Loop (通用执行引擎)                      │
│  └── Short-Term Memory (Ring Buffer)               │
└─────────────────────────────────────────────────────┘
```

---

## 三、核心接口定义

### 3.1 LLM Adapter（仅 Anthropic）

```typescript
interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  toolCalls?: ToolCall[];
  toolResults?: ToolResult[];
}

interface ToolCall {
  id: string;
  name: string;
  arguments: unknown;
}

interface ToolResult {
  content: string;
  isError: boolean;
}

interface ChatResponse {
  message: { role: 'assistant'; content?: string; toolCalls?: ToolCall[] };
  usage: { promptTokens: number; completionTokens: number; totalTokens: number };
  finishReason: 'stop' | 'tool_calls' | 'length' | 'content_filter';
}

interface LLMAdapter {
  /** V1 使用简化签名 `complete(messages, tools?)`。V4 改为 `complete(options: ChatOptions)`（options 对象包含 messages/tools/model/temperature）。详细差异见 V4 architecture.md §2.1 */
  complete(messages: ChatMessage[], tools?: ToolDefinition[]): Promise<ChatResponse>;
}

interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, unknown>;   // JSON Schema
}
```

**关键决策：** 消息类型不依赖任何厂商 SDK。Claude Adapter 负责把统一格式翻译成 Anthropic API 格式。后续加 OpenAI/Google 时只需新增一个实现，不改接口。

### 3.2 Tool Handler Protocol（即插即用工具）

```typescript
interface ToolHandler {
  readonly id: string;           // "filesystem", "git"
  getTools(): ToolDefinition[];   // LLM 可见的工具描述
  execute(call: ToolCall, ctx: ToolExecutionContext): Promise<ToolResult>;
}

class ToolRegistry {
  register(handler: ToolHandler): void;
  async execute(call: ToolCall, ctx: ToolExecutionContext): Promise<ToolResult>;
  getAllTools(): ToolDefinition[];   // 展平所有工具声明，传给 LLM
}
```

**V1 内置工具：**

| ID | 名称 | 功能 |
|----|------|------|
| `filesystem` | Filesystem | read_file, write_file, edit_file, list_dir, grep, grep_r |
| `git` | Git | git_diff, git_status, git_add, git_commit |
| `terminal` | Terminal | exec_command（命令白名单限制） |

**V1 vs V4 差异：** V1 的 ToolHandler 接口仅定义 `id` + `getTools()` + `execute()`。V4 在此基础上增加了 `name`（人类可读名）和 `version`（Semver）。V1 接口设计已考虑前向兼容——后续加 readonly name/version 属性不破坏任何签名，只需更新实现类即可。

### 3.3 Agent（一等公民）

```typescript
interface Agent {
  readonly id: string;
  readonly name: string;
  readonly description: string;   // 用于 Orchestrator 选择 Agent
  systemPrompt: string;          // Agent 的"性格"和行为准则
  model: string;                 // LLM 模型（如 "claude-sonnet-4"）
  temperature?: number;
  maxTokens?: number;             // LLM 单次最大输出 token 数，默认 8192
  contextWindow?: number;         // 模型上下文窗口大小（token），用于 token 预算和压缩触发，默认 200000（Claude Sonnet 4）
  readonly tools: ToolHandler[]; // 本 Agent 可用的工具处理器（只读 — 防止外部篡改）
}

interface ToolExecutionContext {
  sessionId: string;
  agentId: string;
  cwd: string;                    // 工作目录
  allowedPaths?: string[];        // 允许访问的路径列表（安全防御）
}
```

**V1 内置 AgentConfig（纯数据，可 JSON 序列化）：**

```typescript
const BUILTIN_AGENTS: AgentConfig[] = [
  { id: 'orchestrator', name: '编排者', description: '负责分解任务、委派专业 Agent、汇总结果', systemPrompt: '你是多智能体编排系统。你不直接写代码。你的职责：分解任务，使用 delegate_to_agent 委派给专业 Agent，收集结果后返回给用户...' },
  { id: 'coding-agent', name: '编码专家', description: '负责编写、修改、调试代码', systemPrompt: '你是资深开发者。你的职责：编写、修改、调试代码。使用 filesystem 工具读写文件，使用 git 工具查看变更，使用 terminal 执行命令...' },
];

// AgentConfig → Agent 的转换函数（由 Platform 在组装时调用）
function buildAgent(config: AgentConfig, handlers: ToolHandler[], params?: Partial<AgentRuntimeParams>): Agent {
  return {
    ...config,
    model: params?.model ?? DEFAULT_AGENT_PARAMS.model,
    temperature: params?.temperature ?? DEFAULT_AGENT_PARAMS.temperature,
    maxTokens: params?.maxTokens ?? DEFAULT_AGENT_PARAMS.maxTokens,
    contextWindow: params?.contextWindow ?? DEFAULT_AGENT_PARAMS.contextWindow,
    tools: handlers,   // handler 引用由 Platform 注入，不出现在配置文件中
  };
}
```

**关键设计决策：** `AgentConfig`（纯 JSON 数据）与 `Agent`（含 handler 引用）分离。用户通过配置文件定义 Agent 行为，Platform 负责运行时组装 handler。这样改 systemPrompt / model / temperature 不需要重新编译代码。

### 3.4 Universal Agent Loop（通用执行引擎）

所有 Agent 都通过此循环执行：

```typescript
async function runAgentLoop(config: AgentLoopConfig): Promise<AgentResult>

interface AgentLoopConfig {
  agent: Agent;                    // 执行本次循环的 Agent
  messages: ChatMessage[];         // 初始消息列表（不含 system prompt，system 由 Agent.systemPrompt 提供）
  registry: ToolRegistry;          // 工具注册中心（loop 内部通过它执行工具调用）
  ctx: ToolExecutionContext;       // 工具执行上下文（包含 sessionId, cwd, allowedPaths）
  llm: LLMAdapter;                 // LLM 适配器
  memory?: ShortTermMemory;        // 可选，用于 Token 预算 + compact()
  maxIterations?: number;          // 默认 20
  compressionRatio?: number;       // token 预算触发 compact 的比例（相对于 agent.contextWindow），默认 0.8
  signal?: AbortSignal;            // 可选，外部中断信号（Ctrl-C）；loop 每次迭代开始时检查 signal.aborted
}

interface AgentResult {
  status: 'completed' | 'max_iterations_reached' | 'failed' | 'aborted';
  output?: string;         // Agent 的最终输出
  agentId: string;
  error?: string;
}
```

**循环逻辑：**
1. systemPrompt = config.agent.systemPrompt；restMessages = messages（不含 system 角色）；tools = config.tools.map(t => t.getTools()).flat()（由 Platform 组装时注入，V1 简化设计，不通过 loop 内部调 registry.getAllTools()）。将 systemPrompt 作为独立参数传给 LLM Adapter（映射为 Anthropic API 的 `system` 参数），restMessages 放入 `messages` 数组。
2. **每次迭代开始时检查** `config.signal?.aborted` → true 则 return { status: 'aborted', agentId }
3. 如果 LLM 返回工具调用 → 遍历每个 call，通过 `registry.execute(call, ctx)` 执行 → 结果追加到 messages → 回到 1
4. 如果 LLM 只返回文本 → 结束，返回 output
5. 超过 maxIterations → 标记失败

### 3.5 Short-Term Memory（短期记忆）

```typescript
interface ShortTermMemory {
  add(message: ChatMessage): void;
  getContext(): ChatMessage[];   // 获取可用于 LLM 的完整上下文
  /** compact() 返回值是粗略估算：UTF-8 字节数 / 3。精确值需外部 tokenizer，此处仅用于预算判断 */
  compact(): number;             // 压缩旧消息，返回被释放的 token 估算数（UTF-8 bytes / 3）
}
```

**实现：** Ring Buffer。当消息总数超过阈值时，compact() 将最旧的 N 轮对话按角色分类（User/Assistant/Tool）合并为分段摘要，插入一条 `{ role: 'system', content: '[分组摘要]' }`，然后删除被压缩的旧消息。保留角色分类让 LLM 在压缩后仍能区分对话上下文。

**compact() Algorithm (V1):**

```
compact():
  if messages.length <= threshold: return 0

  N = floor(threshold / 2)          // 例：threshold=50 → N=25
  oldestMessages = messages.slice(0, N)

  // 按角色分组
  userMsgs   = oldestMessages.filter(m => m.role === 'user').map(m => m.content)
  assistantMsgs = oldestMessages.filter(m => m.role === 'assistant').map(m => m.content)
  toolResults = oldestMessages.filter(m => m.role === 'tool').map(m => contentOrSummary(m))

  // 每组最多保留 10 条，每条截断至前 200 字符
  group(maxItems, maxChars, items):
    return items.slice(0, maxItems).map(s => s.substring(0, maxChars))

  summary = `
[User Messages]
${group(10, 200, userMsgs).map(m => "- " + m)}

[Assistant Messages]
${group(10, 200, assistantMsgs).map(m => "- " + m)}

[Tool Results]
${group(10, 200, toolResults).map(r => "- " + r)}

[对话摘要：共 ${N} 轮对话，核心目标是 ${userMsgs[0]?.substring(0, 100) || '...'}]`

// 插入摘要到开头
messages.splice(0, N, { role: 'system', content: summary.trim() })

// 返回释放的 token 估算值（UTF-8 bytes / 3）
releasedBytes = oldestMessages.map(m => new TextEncoder().encode(m.content).length).reduce((a, b) => a + b, 0)
return floor(releasedBytes / 3)
```

**设计决策：** V1 使用基于规则的文本摘要（非 LLM 生成），保证零额外成本和确定性行为。V2 可引入 LLM-based summarization 提升摘要质量。`contentOrSummary(m)`：对 tool 角色消息，提取 `m.content` 前 200 字符；若 content 包含 JSON 结构，仅保留外层 key（如 `"write_file(quickSort.ts): success"`）。

### 3.6 Logger（极简日志接口）

```typescript
interface Logger {
  info(msg: string, meta?: Record<string, unknown>): void;
  warn(msg: string, meta?: Record<string, unknown>): void;
  error(msg: string, meta?: Record<string, unknown>): void;
  debug(msg: string, meta?: Record<string, unknown>): void;
}

/** V1 默认实现：输出到 console */
const consoleLogger: Logger = {
  info: (msg, meta) => console.log(`[INFO] ${msg}${meta ? ' ' + JSON.stringify(meta) : ''}`),
  warn: (msg, meta) => console.warn(`[WARN] ${msg}${meta ? ' ' + JSON.stringify(meta) : ''}`),
  error: (msg, meta) => console.error(`[ERROR] ${msg}${meta ? ' ' + JSON.stringify(meta) : ''}`),
  debug: (msg, meta) => { if (process.env.DEBUG === '1') console.debug(`[DEBUG] ${msg}${meta ? ' ' + JSON.stringify(meta) : ''}`); },
};
```

**V1 策略：** 极简实现，仅输出到 console。`debug()` 仅在 `DEBUG=1` 环境变量开启时输出。后续接入 Winston/Pino 等库只需替换默认实现，不改接口。

---

### 3.7 Platform Config（全局配置）

V1 所有可调参数通过 `PlatformConfig` 统一管理，**不硬编码任何运行时值**。配置文件使用 JSON（CLI 场景），后续 Web API 可改为 YAML/TOML。

```typescript
/** ── LLM Provider 配置 ── */
interface LlmConfig {
  provider: 'anthropic';           // V1 特有字段：固定为 'anthropic'。V4 移除此字段（多模型由 model 参数决定）
  apiKey: string;                  // 优先从 config 读取；CLI 场景可 fallback process.env.ANTHROPIC_API_KEY
  baseUrl?: string;                // 默认 https://api.anthropic.com
  timeoutMs?: number;              // HTTP 请求超时（毫秒），默认 30000
}

/** ── Agent 运行时参数（可与 systemPrompt 分离，便于热更新）── */
interface AgentRuntimeParams {
  model: string;                   // LLM 模型 ID（如 "claude-sonnet-4"）
  temperature?: number;            // 采样温度，默认 0.2
  maxTokens?: number;              // LLM 单次最大输出 token 数，默认 8192
  contextWindow?: number;          // 模型上下文窗口大小（token），默认 200000
}

/** ── Agent 定义（不含 handler 引用，handler 由 Platform 组装注入）── */
interface AgentConfig {
  id: string;                      // 唯一标识符
  name: string;                    // 人类可读名称
  description: string;             // 用于 Orchestrator 选择 Agent
  systemPrompt: string;            // 系统提示词（决定 Agent"性格"）
}

/** ── 安全策略配置 ── */
interface SecurityConfig {
  allowedPaths?: string[];         // 默认允许访问的根路径，空数组 = 不限制
  terminalWhitelist?: string[];    // 终端命令白名单，覆盖 TerminalHandler 内置默认值
}

/** ── Session / Loop 配置 ── */
interface RuntimeConfig {
  maxIterations?: number;          // Agent Loop 最大迭代次数，默认 20
  stmThreshold?: number;           // STM compact() 触发阈值（消息条数），默认 50
  compressionRatio?: number;       // token 预算触发 compact 的比例（相对于 contextWindow），默认 0.8
}

/** ── CLI 配置 ── */
interface CliConfig {
  prompt: string;                  // REPL 提示符文本，默认 "Ask me anything: "
}

/** ── 平台顶层配置 ── */
interface PlatformConfig {
  llm: LlmConfig;                 // 必需的：LLM Provider
  agents: AgentConfig[];          // 内置 Agent 列表（不含 handler）
  runtime?: RuntimeConfig;        // 可选：循环/记忆参数
  security?: SecurityConfig;      // 可选：安全策略
  cli?: CliConfig;                // 仅 CLI 场景使用
}

/** ── 配置默认值 ── */
const DEFAULT_CONFIG: Omit<PlatformConfig, 'llm' | 'agents'> = {
  runtime: { maxIterations: 20, stmThreshold: 50, compressionRatio: 0.8 },
  security: { allowedPaths: [], terminalWhitelist: [] },
  cli: { prompt: 'Ask me anything: ' },
};

const DEFAULT_LLM: Partial<LlmConfig> = {
  baseUrl: 'https://api.anthropic.com',
  timeoutMs: 30000,
};

const DEFAULT_AGENT_PARAMS: AgentRuntimeParams = {
  model: 'claude-sonnet-4',
  temperature: 0.2,
  maxTokens: 8192,
  contextWindow: 200000,
};
```

**配置加载流程：**
```
用户启动 CLI → 检查 ~/.agent-platform/config.json → 不存在则使用内置默认值
              ↓
         Platform(config) → 合并 DEFAULT_CONFIG + 用户配置
              ↓
    ClaudeAdapter(config.llm) — apiKey / baseUrl / timeoutMs
    Agent 实例 — systemPrompt + runtime params（model, temperature, maxTokens, contextWindow）分离
    TerminalHandler — whitelist 覆盖内置默认值
    ToolRegistry — allowedPaths 来自 config.security
```

**关键设计决策：**
- `AgentConfig`（纯数据，可 JSON 序列化）与 `Agent`（含 handler 引用，运行时组装）分离。用户通过 AgentConfig 定义行为，Platform 负责注入 handler。
- LLM apiKey 可从配置文件或环境变量读取（config > env > throw）。这样 CI/CD 用环境变量、本地开发用配置文件都支持。
- baseUrl / timeoutMs 放在 config 中，方便切换代理 endpoint 或调试本地模型（如 Ollama）。

**V1 MVP 耦合说明：** Platform constructor 直接 `new FilesystemHandler/GitHandler/TerminalHandler` 是 V1 的可接受简化——只有 3 个固定工具，不存在生态扩展需求。若未来需解耦，可抽 `createHandlers(config)` 工厂函数。

### 3.8 Session Manager（会话管理）

```typescript
class SessionManager {
  async create(agentId: string, projectRoot: string): Promise<Session>;
  get(id: string): Session | undefined;
  async end(sessionId: string): void;
}

interface Session {
  id: string;
  agentId: string;
  projectRoot: string;
  stm: ShortTermMemory;          // 会话级对话历史
}
```

**V1 并发策略：** 进程内 Map + per-session async mutex。每个 Session 有独立的锁，防止多终端同时操作同一项目时的竞态。STM 是进程内内存 Ring Buffer，不持久化。Session 生命周期与 CLI 进程绑定（退出即销毁）。

> **MVP 限制说明：** V1 Sessions **不会持久化到磁盘**。CLI 进程退出后所有会话数据丢失。这是有意为之的 MVP 决策——V2 引入 SQLite 持久化时，`persistSessionSummary()` 和 `recover()` 方法会加入实现。当前不碰任何磁盘 I/O。

**说明：** V1 不需要跨会话持久化记忆（LTM/Vector Store 推迟到 Phase 2），因此 Session Manager 仅做运行时会话管理，不涉及任何磁盘写入。

---

## 四、多 Agent 协作流程 (V1 核心场景)

```
用户说: "帮我实现一个快速排序函数"
  │
  ▼ Orchestrator Agent
  │ LLM 识别到这是一个编码任务 → delegate_to_agent(coding-agent, "实现快速排序")
  │
  ▼ Coding Agent
  │ ├── LLM ↔ Tools Loop:
  │ │   write_file(quickSort.ts) → git_diff → read_file(...)
  │ │   ... 反复迭代直到完成 ...
  │ └── output: "已完成 quickSort 实现"
  │
  ▼ Orchestrator 返回给用户
```

**委派机制：** Orchestrator 识别到编码任务后，通过内部调用触发 Coding Agent（复用 Universal Loop）。Coding Agent 执行完毕后返回结果给 Orchestrator，Orchestrator 再返回给用户。

---

## 五、安全策略 (V1)

| 威胁 | 防御方式 |
|------|----------|
| **文件越权访问** | `allowedPaths` — 工具执行前校验路径在允许目录内 |
| **危险命令执行** | terminal 工具限制为白名单命令（cat, grep, ls, echo, git, mkdir, cp, mv, rm, touch, node...） |
| **无限循环** | maxIterations 限制 Agent Loop 轮次（默认 20） |

---

## 六、Monorepo 包结构 (V1)

```
agent-platform/
├── packages/
│   ├── shared-types/          # ChatMessage, ToolCall, Agent, PlatformConfig...
│   ├── llm-adapter/           # Anthropic Claude Adapter 实现
│   ├── tool-core/             # ToolRegistry + runAgentLoop
│   ├── tools/
│   │   ├── filesystem/        # read_file, write_file, grep, grep_r...
│   │   ├── git/               # git_diff, git_status...
│   │   └── terminal/          # exec_command (白名单)
│   ├── memory-stm/            # Ring Buffer 短期记忆（⚠️ V1 不依赖 hook-core）
│   └── platform/              # 组装一切（不含 CLI 入口，见 apps/cli/）
├── apps/
│   └── cli/                   # CLI 入口（独立包，依赖 platform + esbuild 打包）
└── package.json               # pnpm workspace root（tests/ 由根 vitest 直接管理，不是 workspace package）
```

**V1 不拆分的理由：** 包数量少，拆分增加维护负担。等 V2 扩展生态时再拆分。CLI 独立为 `apps/cli/` 是为了遵循 monorepo 惯例（应用层与库层分离），不影响运行时行为。

---

## 七、演进路径

```
Phase 1 (V1): 编码智能体 MVP
  ├── Anthropic Claude Adapter
  ├── filesystem, git, terminal 工具
  ├── Orchestrator + Coding Agent
  └── CLI

Phase 2: 扩展生态
  ├── OpenAI/Google Adapter
  ├── Plugin System + Hook Bus
  ├── Skill System (模板引擎)
  ├── LTM + Vector Store
  ├── TDD / Security 官方插件
  └── Web API

Phase 3: 生产级
  ├── Multi-user / RBAC
  ├── Circuit Breaker / Fallback Chain
  ├── Rate Limiter / Quota Management
  ├── IDE Extension / Slack Bot
  └── K8s Deployment
```

---

## 八、关键设计决策 (V1)

### Q: 为什么 V1 只用 Claude？
A: MVP 目标是验证架构，不是做多模型兼容。Claude 的 native tool use 功能最成熟。后续加 OpenAI/Google 只需新增一个 Adapter 实现，不改接口。

### Q: 为什么 Orchestrator 本身也是一个 Agent？
A: 统一抽象。所有 Agent（包括编排者）共享同一个 Universal Loop，减少代码重复。未来用户可以定义自己的"编排者变体"。

### Q: 为什么 V1 不要 Plugin/Skill/Hook 系统？
A: V1 只有两个内置 Agent，不需要第三方扩展。Plugin Manager、Skill Registry、Hook Bus 这些系统的实现量很大，且会引入额外的复杂度和 bug 面。等核心架构验证后再加。

### Q: 为什么不用 Monorepo 拆分包？
A: V1 只有 6-7 个包，拆分增加维护负担（每个包的 package.json、测试、发布流程）。等 V2 有 20+ 包时再拆分。运行时行为不受影响。

---

## 九、V4 vs V1 差异对照

> `architecture.md`（v4）是完整平台架构，包含大量 V1 不需要的特性。实现 V1 时以本文档为准。

| 接口/组件 | V4 定义 | V1 裁剪 |
|-----------|---------|---------|
| **LLMAdapter** | `complete() + stream() + completeWithSchema()` + `capabilities` | 仅 `complete()`，无流式、无结构化输出 |
| **ToolHandler** | `id` + `name` + `version` + `getTools()` + `execute()` | 仅 `id` + `getTools()` + `execute()` |
| **Agent.systemPrompt** | 可变（可运行时修改） | 固定，构建时确定 |
| **Agent.skills** | Skill ID 列表，运行时激活 | 无 Skill System |
| **Agent.memory / AgentMemory** | 跨会话持久化记忆（knowledge/experience/preferences） | 无 |
| **AgentRegistry** | 注册/查询/推荐/卸载 Agent | V1 只有两个固定 Agent，无需 Registry |
| **SessionManager** | AsyncMutex + projectLock + recover() + maxSessions eviction + listByProject() | 仅 `create()` / `get()` / `end()` |
| **Agent Loop** | Token budget + STM compact + Hook 集成 + 文件级锁 + delegationDepth 追踪 | LLM → Tool → LLM 循环 + token budget（contextWindow * compressionRatio）+ STM compact |
| **HookBus / HookEvent** | 完整事件总线（12+ 事件类型） | 无 |
| **PluginManager / PluginContext** | 生命周期管理、依赖解析、热重载 | 无 |
| **SkillRegistry** | 发现/加载/激活/模板渲染 | 系统提示词硬编码在 Agent 定义中 |
| **TokenBucket / RateLimiter** | 令牌桶算法，按模型独立限速 | 无 |
| **QuotaManager** | CLI 层配额跟踪（SQLite） | 无 |
| **PlatformConfig** | 完整配置结构（llm/storage/security/delegation/rateLimiting/observability/agentOverrides） | V1 定义简化版：llm + agents(纯数据) + runtime + security + cli；不含 storage/delegation/rateLimiting/observability |
| **Session.formatVersion / migrateSessionFormat()** | Session 格式版本迁移 | 无，V1 只有单一格式 |

---

> **文档版本：** v1.0 | **最后更新：** 2026-05-20
> 此文档是 V1 的**精简版架构**。详细实现细节在代码中通过 TDD 逐步演化，不在本文档中定义。
