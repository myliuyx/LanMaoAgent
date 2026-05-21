# AI Agent Platform — 架构设计 v4 (Multi-Agent)

> 核心目标：**强解耦、可演进**。从编码智能体起步，未来平滑扩展到全能多智能体平台。
> **扩展性支柱：Plugin + Skill + Hook** — 不碰一行核心代码就能改变平台行为。
> **一等公民：Agent** — Agent 不是配置对象，是有身份、能力、工具集、记忆、技能的独立实体。Orchestrator 本身就是一个 Agent。

---

## ⚠️ V1 实现者必读（重要）

> **V1 实现请只看 `architecture-v1.md` + `v1-implementation-steps.md`。**
> 本文档是 V4 全平台架构，包含大量 V1 不需要的特性。以下列出 V1 **不需要碰**的接口/组件：

| V4 特性 | V1 状态 | 说明 |
|---------|---------|------|
| `LLMAdapter.stream()` / `completeWithSchema()` | **跳过** | V1 只有非流式 `complete(messages, tools?)`（签名与 V4 的 `complete(options: ChatOptions)` 不同） |
| `ToolHandler.name` / `ToolHandler.version` | **跳过** | V1 只有 `id` |
| `AgentMemory` / `ExperienceEntry` | **跳过** | V1 无跨会话 Agent 记忆 |
| `AgentRegistry.recommend()` | **跳过** | V1 只有两个固定 Agent，无需推荐 |
| `PluginManager` / `PluginContext` | **跳过** | V1 无 Plugin System |
| `SkillRegistry` / `SkillBundle` | **跳过** | V1 系统提示词硬编码 |
| `HookBus` / `HookEvent` / `HookRegistration` | **跳过** | V1 无 Hook 机制 |
| `SessionManager.AsyncMutex` / `recover()` / `maxSessions` eviction | **跳过** | V1 只有简单 create/get/end |
| `CircuitBreaker` / `FallbackChain` | **跳过** | V1 只用 Claude，无降级需求 |
| `RateLimiter` / `TokenBucket` / `QuotaManager` | **跳过** | V1 不涉及速率限制 |
| `PlatformConfig` 完整定义 | **跳过** | V1 使用简单配置即可 |
| `Session.formatVersion` / `migrateSessionFormat()` | **跳过** | V1 只有 v1 一个格式 |
| Web API (`apps/web-api`) | **跳过** | V1 只做 CLI |
| 多用户 / RBAC / tenant_id | **跳过** | V1 单用户本地使用 |

> **总结：** V4 文档中的接口定义可能比 V1 需要的更多。实现时以 `architecture-v1.md` 为准，它定义了 V1 需要的所有接口和组件。

---

## 一、架构总览 (Multi-Agent)

```
┌──────────────────────────────────────────────────────────────────────┐
│                    API / CLI Layer                                   │
│                  (用户交互入口)                                         │
├──────────────────────────────────────────────────────────────────────┤
│                        User Request                                  │
│                            │                                         │
│                            ▼                                         │
│              ┌─────────────────────────┐                             │
│              │   Orchestrator Agent    │  ◄── Orchestrator 本身是Agent
│              │   (编排者)               │                               │
│              │                         │                               │
│              │  职责:                   │                               │
│              │  • 分解任务              │                               │
│              │  • 选择 Agent            │                               │
│              │  • 收集结果              │                               │
│              └───────┬─────────────────┘                             │
│                      │                                                │
│          ┌───────────┼───────────┬───────────┐                       │
│          ▼           ▼           ▼           ▼                        │
│   ┌─────────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐             │
│   │ Coding Agent │ │ Review   │ │ Test   │ │ Research │  ...         │
│   │ (编码者)     │ │ Agent    │ │ Agent  │ │ Agent    │               │
│   │              │ │ (审查者) │ │ (测试) │ │ (调研)   │               │
│   └──────┬──────┘ └────┬─────┘ └───┬────┘ └────┬─────┘             │
│          │              │           │           │                     │
│          └──────────────┴───────────┴───────────┘                     │
│                            │                                          │
│       ┌────────────────────┼────────────────────┐                    │
│       ▼                    ▼                    ▼                     │
│  LLM Adapter           Tool Registry      Memory Manager             │
│  (任何LLM)            (即插即用工具)       (三层记忆)                  │
│       │                    │                    │                     │
│   ┌───┴──────┐        ┌───┴────────┐    ┌─────┼─────────┐            │
│   ▼          ▼        ▼            ▼    ▼      ▼         ▼           │
│ Claude OpenAI … Git Terminal STM LTM Vector                     │       │
│                                                                                   │
│  ┌──────────────────────────────────────────────────────────┐             │
│  │         Plugin Manager (生命周期管理)                    │             │
│  │  ┌──────────┐    ┌──────────┐                           │             │
│  │  │ Plugins  │───►│  Skills  │  (文本注入Prompt)        │             │
│  │  │(代码扩展) │    │(知识注入) │                           │             │
│  │  └──────────┘    └──────────┘                           │             │
│  │              Hook Bus ◄──── 运行时拦截点                │             │
│  └──────────────────────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────────────────┘
```

**Agent vs Orchestrator：**

| | Agent (任意类型) | Orchestrator Agent (特殊类型) |
|---|---|---|
| **身份** | 有名称、描述、人格 | "编排者"，无固定人格 |
| **能力** | 专注特定领域（编码/审查/测试） | 通用任务分解 + Agent 路由 |
| **工具集** | 领域专属工具（如 filesystem, git） | `delegate_to_agent`, `report_completion`, `write_log` |
| **职责** | 完成具体任务 | 规划、委派、协调 |

**扩展性支柱：**

| 层 | 是什么 | 做什么 | 谁写 |
|---|--------|--------|------|
| **Plugin** | JS/TS 模块，有生命周期 | 注册工具、Hook、声明 Skill、定义新 Agent | 开发者（可第三方） |
| **Skill** | YAML + Markdown 文本包 | 注入系统提示词，引导 Agent 行为 | 任何人（含非程序员） |
| **Hook** | 事件驱动的拦截点 | 在运行时修改/观察/阻断流程 | Plugin 注册，用户配置 |

---

## 二、核心接口定义

### 2.1 LLM Adapter (可替换任何大模型)

```typescript
interface LLMAdapter {
  complete(options: ChatOptions): Promise<ChatResponse>;     // 非流式
  stream(options: ChatOptions): AsyncIterable<StreamChunk>;  // 流式
  completeWithSchema<T>(options: ChatOptions, schema: ZodType<T>): Promise<T>;

  readonly capabilities: LLMCapabilities;   // 运行时能力探测（工具调用、结构化输出、多模态等）
}

/** 各 Adapter 实现通过此接口暴露自身能力，调用方据此决定使用哪种 API */
interface LLMCapabilities {
  supportsToolCalling: boolean;       // 是否支持原生工具调用
  supportsSchemaOutput: boolean;      // 是否支持 structured output / JSON mode
  supportsVision: boolean;            // 是否支持多模态（图片/文件）
}

interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  toolCalls?: ToolCall[];
  toolResults?: ToolResult[];
}

/** ── LLM 调用选项 ── */
interface ChatOptions {
  messages: ChatMessage[];
  model?: string;
  temperature?: number;
  maxTokens?: number;
  tools?: ToolDefinition[];        // 本次调用可用的工具声明（由 Adapter 翻译为厂商格式）
}

/** LLM 流式响应块 — usage 累积策略见下方说明 */
interface StreamChunk {
  content?: string;               // 增量文本内容
  toolCalls?: PartialToolCall[];  // 增量工具调用参数（流式时分片到达）
  usage?: TokenUsage;             // 可选，通常在最后一个 chunk 中提供完整用量；也可能每 chunk 返回增量值
  done: boolean;                  // 是否为最后一个 chunk
}

/** ── LLM 响应 ── */
interface ChatResponse {
  message: { role: 'assistant'; content?: string; toolCalls?: ToolCall[] };
  usage: TokenUsage;
  finishReason: 'stop' | 'tool_calls' | 'length' | 'content_filter';
}

/** Token 用量统计，包含可选的 cache 字段 */
interface TokenUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  /** Claude API：cache_read token 数（从缓存读取的历史消息） */
  cacheReadTokens?: number;
  /** Claude API：cache_creation token 数（写入新缓存的 token） */
  cacheCreationTokens?: number;
}

/** ── 工具调用（LLM 发出的完整调用）── */
interface ToolCall {
  id: string;                     // LLM 生成的调用 ID，用于关联结果
  name: string;                   // 工具名称
  arguments: unknown;             // 解析后的参数对象
}

/** ── 流式工具调用的部分片段（逐步拼接）── */
interface PartialToolCall {
  id?: string;
  name?: string;
  arguments?: string;            // 未解析的 JSON 字符串，需要累积后 parse
}

/** 流式 PartialToolCall 合并策略 — 每个 chunk 携带独立 ID，按 ID 分组后拼接 */
interface ToolCallAccumulator {
  private chunks: Map<string, { name?: string; argParts: string[] }>;

  /** 累积一个流式 chunk；如果 id 已存在则追加到 argParts */
  append(chunk: PartialToolCall): void {
    if (!chunk.id) return;  // 无 ID 的 chunk 忽略
    const entry = this.chunks.get(chunk.id) ?? { name: undefined, argParts: [] };
    if (chunk.name !== undefined) entry.name = chunk.name;
    if (chunk.arguments !== undefined) entry.argParts.push(chunk.arguments);
    this.chunks.set(chunk.id, entry);
  }
  
  /** 检查某个 ID 是否已完成（stream done === true） */
  isComplete(id: string): boolean { /* ... */ return false; }
  
  /** 将所有累积的 PartialToolCall 合并为完整的 ToolCall[] */
  finalize(): ToolCall[] {
    const results: ToolCall[] = [];
    for (const [id, entry] of this.chunks) {
      try {
        results.push({
          id,
          name: entry.name ?? 'unknown',
          arguments: JSON.parse(entry.argParts.join('')),
        });
      } catch { /* 解析失败则丢弃该调用 */ }
    }
    return results;
  }
  
  /** 重置（新请求开始时调用） */
  reset(): void { this.chunks.clear(); }
}

/** ── 工具声明（LLM 可看到的工具描述）── */
interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, unknown>;   // JSON Schema（Adapter 负责翻译为各厂商格式）
}

/** ── 工具执行结果 ── */
interface ToolResult {
  content: string;               // 工具输出内容（给 LLM 看的）
  isError: boolean;              // 是否出错
}

/** ── 工具执行上下文（每个 Session 独立，包含权限边界）── */
interface ToolExecutionContext {
  sessionId: string;             // 当前会话 ID
  agentId: string;               // 当前 Agent ID
  cwd: string;                   // 工作目录
  allowedPaths?: string[];       // 允许访问的路径列表
  permissions?: Permission[];    // 当前会话/Agent 被授予的权限列表
  delegationDepth?: number;      // 当前 Session 的委派深度，由 Platform 自动维护
  traceId?: string;              // 追踪 ID
}

```

**关键决策：** 所有消息类型统一为 `ChatMessage`，不依赖任何厂商 SDK。Adapter 负责把统一格式翻译成各厂商的特定格式（OpenAI 的 function calling vs Anthropic 的 native tool use）。

### 2.2 Tool Handler Protocol (即插即用工具) — 已重命名避免与 Plugin 混淆

```typescript
// ── 模块级工具函数：从 ToolCall.arguments 中提取文件路径（在 class 外部定义）──

/**
 * 从 ToolCall.arguments 中提取所有文件路径。
 * 先 JSON.parse → 递归遍历对象树，只匹配精确键名 path/filepath（避免 pathname 等误匹配）。
 */
function extractAllowedPathsFromArgs(args: unknown): string[] {
  const paths: string[] = [];
  if (args === null || args === undefined) return paths;

  const obj = typeof args === 'string' ? JSON.parse(args) : args;

  function walk(v: unknown, key: string): void {
    if (key === 'path' || key === 'filepath') {
      if (typeof v === 'string' && v.length > 0) paths.push(v);
    } else if (typeof v === 'object' && v !== null) {
      if (Array.isArray(v)) {
        for (let i = 0; i < v.length; i++) walk(v[i], String(i));
      } else {
        const entries = Object.entries(v as Record<string, unknown>);
        // eslint-disable-next-line @typescript-eslint/no-shadow
        for (const [k, val] of entries) walk(val, k);
      }
    }
  }

  if (typeof obj === 'object' && obj !== null && !Array.isArray(obj)) {
    const entries = Object.entries(obj as Record<string, unknown>);
    // eslint-disable-next-line @typescript-eslint/no-shadow
    for (const [k, val] of entries) walk(val, k);
  }

  return paths;
}

// 注意：原 ToolPlugin 接口已更名为 ToolHandler，避免与 plugin-core 中的 Plugin 宽接口混淆。
// ToolHandler 是窄接口，只定义单个工具的声明和执行；Plugin 是宽接口，一个 Package 可同时提供工具、Skill 引用和 Hook 注册。

interface ToolHandler {
  readonly id: string;           // "filesystem", "git"
  readonly name: string;         // 人类可读名称
  readonly version: string;      // Semver
  
   /** 实现方可在此缓存结果，避免每次迭代都重新创建 */
  getTools(): ToolDefinition[];
  execute(call: ToolCall, ctx: ToolExecutionContext): Promise<ToolResult>;
}

class ToolRegistry {
  private hookBus: HookBus;


  register(handler: ToolHandler): void;

  constructor(hookBus: HookBus) { this.hookBus = hookBus; }

  /**
   * 执行工具调用。先 emit tool:beforeExecute Hook，
   * 如果 Hook 设置了 error（如安全拦截），则跳过实际执行。
   */
  async execute(call: ToolCall, ctx: ToolExecutionContext): Promise<ToolResult> {
    // allowedPaths 校验 — 在 Hook 之前检查路径权限，使用 path.resolve + startsWith 规范化比较
    if (ctx.allowedPaths?.length) {
      const paths = extractAllowedPathsFromArgs(call.arguments);
      
      for (const p of paths) {
        try {
          const resolved = require('path').resolve(p);
          const allowedResolved = ctx.allowedPaths.map(a => require('path').resolve(a));
          if (!allowedResolved.some(allowed => resolved.startsWith(allowed))) {
            return { content: `Access denied: path '${p}' is outside allowedPaths`, isError: true };
          }
        } catch { /* 非路径参数忽略 */ }
      }
    }

    // 1. 前置 Hook 拦截（安全检查、权限验证）
    const preResult = await this.hookBus.emit('tool:beforeExecute', {
      toolId: call.name, toolCall: call, context: ctx
    });
    
    if (preResult.blocked) {
      // Hook 链中有 Handler 设置了 error → 阻断执行，但仍 emit afterExecute
      const blockedResult = { content: preResult.blockReason!, isError: true };
      await this.hookBus.emit('tool:afterExecute', { results: [blockedResult] });
      return blockedResult;
    }

    // 2. 查找对应 Handler 并执行
    const handler = this.findHandler(call.name);
    if (!handler) {
      const unknownResult = { content: `Unknown tool: ${call.name}`, isError: true };
      await this.hookBus.emit('tool:afterExecute', { results: [unknownResult] });
      return unknownResult;
    }
    
    try {
      const result = await handler.execute(call, ctx);
      // 成功时也 emit afterExecute，供 TDD/审计使用
      await this.hookBus.emit('tool:afterExecute', { results: [result] });
      return result;
    } catch (err) {
      // Tool 执行失败 → emit error:caught + tool:afterExecute，继续流程不中断
      const errorResult = { content: `Tool execution error: ${formatError(err)}`, isError: true };
      await this.hookBus.emit('tool:afterExecute', { results: [errorResult] });
      await this.hookBus.emit('error:caught', {
        error: err as Error, meta: { toolId: call.name }
      });
      return errorResult;
    }
  }

  getAllTools(): ToolDefinition[];   // 展平所有工具声明(LLM 用)
}
```

### 2.3 Memory (三层记忆)

```typescript
// STM — Ring Buffer + 自动压缩
interface ShortTermMemory {
  add(message: ChatMessage): Promise<void>;    // 超出上下文窗口时自动压缩旧消息
  getContext(): ChatMessage[];                  // 获取可用于 LLM 的完整上下文
  
  /** 压缩策略 — 按以下优先级释放 token 预算：
   * 1. 首先摘要合并最旧的 N 轮对话（保留关键信息）
   * 2. 如果摘要后仍超限，丢弃已摘要的原始消息
   * 3. 最后手段：移除 tool result 内容（只保留工具名称和是否成功），LLM 可根据名称重放 */
  compact(): Promise<number>;   // 返回被压缩掉的 token 数
}

// LTM — KV + 分类标签
interface LongTermMemory {
  set(key: string, value: string, category: Category, tags?: string[]): Promise<void>;
  query(filters?: QueryFilters): Promise<Entry[]>;
  
  /** 生成知识摘要注入 Prompt */
  buildContextPrompt(maxTokens: number): Promise<string>;
}

// Vector — Embedding + KNN
interface VectorMemoryStore {
  index(content: string, metadata: Record<string, unknown>, ttlMs?: number): Promise<string>;   // 可选 TTL，过期后自动标记为不可检索
  search(query: string, k?: number): Promise<SearchResult[]>;
  
  /** 清理过期的条目，返回被删除的数量 */
  cleanupExpired(): Promise<number>;
}

interface SearchResult {
  id: string;
  content: string;
  score: number;            // 相似度分数 (0-1)
  metadata?: Record<string, unknown>;
  expiresAt?: number;       // 过期时间戳（毫秒）
}
```

**三层关系：**
- **STM**: 会话级，Ring Buffer，自动压缩，存储对话历史。支持 `compact()` 释放 token 预算。
- **LTM**: 项目级，KV 存储，显式保存学到的知识（技术栈、决策、偏好）。
- **Vector**: 语义级，Embedding 向量，支持模糊匹配和代码检索。

### 2.4 Agent — 一等公民 (v4 核心重构)

**Agent 不是配置对象。Agent 是有身份、能力边界、工具集、记忆、技能的独立实体。**

```typescript
/** Agent 是一等公民 —— 有身份、人格、能力、工具、记忆、技能 */
interface Agent {
  /** ── 身份 ── */
  readonly id: string;                   // 唯一标识，如 "coding-agent", "research-agent"
  readonly name: string;                 // 人类可读名称，如 "编码专家"
  readonly description: string;          // 简短描述（用于 Orchestrator 选择 Agent）
  readonly version: string;              // Semver

  /** ── 人格 (System Prompt) ── */
  systemPrompt: string;

  /** ── 能力 (LLM 配置) ── */
  model: string;                         // 首选模型
  fallbackModels?: string[];             // 降级模型列表，按顺序尝试
  temperature?: number;                  // 温度参数
  maxTokens?: number;                    // 最大输出 token

  /** ── 工具集 (本 Agent 可用的工具，只读 — 防止外部篡改) ── */
  readonly tools: ToolHandler[];         // 本 Agent 专属的工具处理器
  
  /** ── 记忆 (每个 Agent 有独立的 STM + LTM 访问权限) ── */
  memory?: AgentMemory;                  // 可选：Agent 级长期记忆（跨会话持久化）

  /** ── 技能 (运行时激活的 Skill) ── */
  skills: string[];                      // 本 Agent 默认激活的 Skill ID 列表
  
  /** ── 元数据 ── */
  metadata?: Record<string, unknown>;    // 扩展字段（标签、权限等级等）
}

/** 
 * Agent 级记忆 —— 每个 Agent 有自己的长期知识，跨会话持久化。
 * 与 Session 级的 LTM 不同：Session LTM = 项目共享；Agent Memory = Agent 专属。
 */
interface AgentMemory {
  /** Agent 的专属知识库 (KV) — 使用 Record 而非 Map，确保可 JSON 序列化持久化 */
  knowledge: Record<string, string>;     // key-value 知识存储
  
  /** Agent 的专业经验（从完成任务中学习的模式） */
  experience: ExperienceEntry[];         // 成功/失败的模式记录
  
  /** Agent 的风格偏好（编码风格、命名习惯等） */
  preferences: Record<string, unknown>;  // 个人偏好
  
  /** 持久化到磁盘 — 将 knowledge / experience / preferences 序列化为 JSON */
  save(): Promise<void>;
  
  /** 从磁盘加载 — 反序列化 JSON 恢复状态 */
  load(): Promise<void>;
}

interface ExperienceEntry {
  taskId: string;
  outcome: 'success' | 'failure';
  pattern: string;           // "当遇到 X 情况时，用 Y 方案有效"
  timestamp: number;
}
```

**用户如何定义 Agent（两种方式）：**

```typescript
// 方式一：直接配置 (快速上手)
const myAgent: Agent = {
  id: 'code-reviewer',
  name: '代码审查专家',
  description: '专注代码质量、安全漏洞和性能优化',
  version: '1.0.0',
  systemPrompt: `你是一位资深代码审查专家。你的职责：
    1. 检查代码逻辑正确性
    2. 识别潜在安全漏洞（SQL注入、XSS等）
    3. 评估性能影响
    4. 给出改进建议`,
  model: 'claude-opus-4',
  temperature: 0.1,
  tools: [gitDiffHandler, readFileHandler],
  skills: ['owasp-security-review'],
};

// 方式二：通过 Plugin 定义 (可发布、可复用)
class CodeReviewerPlugin implements Plugin {
  manifest = { id: 'code-reviewer', name: 'Code Review Agent', ... };

  // getTools 是异步方法，插件可在此做异步初始化
  async getTools(): Promise<ToolHandler[]> {
    return [securityScanHandler, diffViewerHandler];
  }

  async onLoad(ctx: PluginContext): Promise<void> {
    // 定义 Agent（不是配置！是完整的 Agent 实例）
    const agent: Agent = {
      id: 'code-reviewer',
      name: '代码审查专家',
      systemPrompt: /* ... */,
      tools: await this.getTools(),
      skills: ['owasp-security-review'],
      memory: { knowledge: {}, experience: [], preferences: {} },  // Agent 专属记忆（Record 可序列化）
    };

    // 注册到 Agent Registry
    ctx.agents.register(agent);

    // 注册 Hook（如：审查完成后自动提交报告）
    const _submitReport = async (hookCtx: BaseHookContext) => { /* ... */ };
    ctx.hooks.on('agent:afterLoop', _submitReport, { priority: 100 });
  }
}
```

**Orchestrator Agent — 编排者本身就是 Agent：**

```typescript
/** 
 * Orchestrator Agent —— 它不是独立的管理器类，而是一个特殊的 Agent。
 * 它的"人格"是任务分解和 Agent 路由，它的工具集包含委派其他 Agent 的能力。
 */
const orchestratorAgent: Agent = {
  id: 'orchestrator',
  name: '编排者',
  description: '负责接收复杂请求、分解任务、委派给专业 Agent、汇总结果',
  version: '1.0.0',

  /** Orchestrator 的系统提示 —— 告诉它"你是指挥官，不是执行者" */
  systemPrompt: `你是一个多智能体编排系统。你不直接写代码或做测试。
    你的职责：
    1. 接收用户的复杂请求
    2. 将任务分解为子任务
    3. 根据子任务类型，选择最合适的 Agent 执行
    4. 收集各 Agent 的结果并汇总
    
    你使用 delegate_to_agent 工具来委派任务。
    每个委派返回 { agentId, output }，你需要追踪已完成的任务数。
    当所有子任务完成后，你必须调用 report_completion 向用户返回最终结果。
    不调用 report_completion 会导致对话无限循环。`,

  /** Orchestrator 的模型 —— 需要强推理能力 */
  model: 'claude-opus-4',
  temperature: 0.3,   // 需要一定创造性来分解任务
  
  /** 
   * Orchestrator 的工具集 —— 核心工具是"委派给其他 Agent"，
   * 加上通用的文件读取、写日志等辅助工具。
   */
  tools: [
    delegateToAgentHandler,     // ★ 核心：将子任务委派给指定 Agent
    createTaskGroupHandler,     // 创建并行的任务组（并行委派）
    collectResultHandler,       // 收集已完成的 Agent 结果
    reportCompletionHandler,    // ★ 标记所有子任务完成，返回最终结果给用户
    writeLogHandler,            // 写执行日志（辅助）
    readFileHandler,            // 读取文件（辅助，用于了解上下文）
  ],

  /** Orchestrator 的技能 —— 编排相关的 Skill */
  skills: ['task-planning', 'agent-routing'],   // 编排技能包
  
  metadata: { role: 'orchestrator' },
};
```

**Agent 委派工具 (delegate_to_agent)：**

```typescript
/** 
 * Orchestrator Agent 的核心工具 —— 将子任务委派给其他 Agent。
 * 这是多 Agent 协作的关键：一个 Agent（Orchestrator）通过工具调用触发另一个 Agent 的执行。
 */

/** 默认委派深度上限 — 实际值从 PlatformConfig.delegation.maxDepth 读取 */
const DEFAULT_MAX_DELEGATION_DEPTH = 5;  // 嵌套委派深度上限

interface DelegateArgs {
  agentId: string;
  task: string;
  context?: {
    files?: string[];
    previousResults?: Record<string, unknown>;
  };
}

interface DelegateToAgentHandler implements ToolHandler {
  id = 'delegate_to_agent';
  name = 'Delegate to Agent';

  getTools(): ToolDefinition[] {
    return [{
      name: 'delegate_to_agent',
      description: '将子任务委派给指定的专业 Agent。返回该 Agent 的执行结果。',
      // 接口层用 JSON Schema，Adapter 负责翻译为各厂商格式
      parameters: {
        type: 'object',
        properties: {
          agentId: { type: 'string', description: '目标 Agent ID，如 "coding-agent", "test-agent"' },
          task: { type: 'string', description: '要执行的具体任务描述' },
          context: {
            type: 'object',
            properties: {
              files: { type: 'array', items: { type: 'string' } },
              previousResults: { type: 'object' },
              // delegationDepth 已由 runAgentLoop 内部自动累加
            },
          },
        },
        required: ['agentId', 'task'],
      },
    }];
  }

  async execute(call: ToolCall, ctx: ToolExecutionContext): Promise<ToolResult> {
    const args = call.arguments as DelegateArgs;
    
    // 1. 查找目标 Agent（从 AgentRegistry）
    const targetAgent = agentRegistry.get(args.agentId);
    if (!targetAgent) {
      return { content: `Unknown agent: ${args.agentId}`, isError: true };
    }

    // 2. 创建子任务 Session（隔离的会话上下文）
    const subSession = await sessionManager.create({
      sessionId: `sub-${crypto.randomUUID()}`,  // 子任务 Session ID
      agentId: args.agentId,                     // 使用 agentId（Agent 是一等公民）
      projectRoot: ctx.cwd ?? '.',
    });

    // 执行目标 Agent（复用 Universal Agent Loop，但传入目标 Agent 的配置）
    // delegationDepth 由 runAgentLoop 从 context 读取，不再信任 LLM 传入
    // 重试 + 降级逻辑
    const delegateConfig = {
      agent: targetAgent,          // ★ 不是 config，是完整的 Agent 实例
      messages: [
        { role: 'system', content: targetAgent.systemPrompt },
        { role: 'user', content: args.task },
      ],
      memory: subSession.stm,
      tools: targetAgent.tools,
      maxIterations: 15,           // Agent 委派有自己的迭代上限
      context: { ...ctx, delegationDepth: (ctx.delegationDepth ?? 0) + 1 },  // 基于上下文深度自动 +1
    };

    let result: AgentResult;
    const maxRetries = 2;
    const baseBackoffMs = 1000;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        result = await runAgentLoop(delegateConfig);
        break; // 成功则退出重试循环
      } catch (err) {
        if (attempt < maxRetries) {
          const backoffMs = baseBackoffMs * Math.pow(2, attempt); // 指数退避：1s → 2s
          await sleep(backoffMs);
          continue;
        }
        // 重试用尽，尝试降级到推荐分数 > 0.5 的替代 Agent
        const alternatives = agentRegistry.recommend(args.task)
          .filter(r => r.agent.id !== args.agentId && r.score > 0.5);
        
        let fallbackSucceeded = false;
        for (const alt of alternatives) {
          try {
            result = await runAgentLoop({ ...delegateConfig, agent: alt.agent });
            fallbackSucceeded = true;
            break;
          } catch {}
        }
        
        if (!fallbackSucceeded) {
          throw err; // 所有策略用尽，向上传播错误
        }
      }
    }
    
    // ★ Session 必须清理，防止泄漏（重试+降级完成后统一 end）
    await sessionManager.end(subSession.id);

    // 4. 返回结果给 Orchestrator
    return { 
      content: JSON.stringify({ agentId: args.agentId, output: result.output }),
      isError: false 
    };
  }
}
```

### 2.5 Agent Registry — Agent 注册中心 (v4 新增)

```typescript
/** 
 * Agent Registry —— 管理所有已注册的 Agent。
 * 由 Platform 在启动时构建，Plugin 通过 PluginContext.agents.register() 添加新 Agent。
 */
class AgentRegistry {
  private agents = new Map<string, Agent>();

  /** 注册一个 Agent（Plugin onLoad 时调用） */
  register(agent: Agent): void { this.agents.set(agent.id, agent); }

  /** 按 ID 获取 Agent，未找到则抛错 */
  get(id: string): Agent {
    const a = this.agents.get(id);
    if (!a) throw new Error(`Agent not found: ${id}`);
    return a;
  }

  /** 列出所有可用 Agent（用于 Orchestrator 选择） */
  list(): Agent[] { return Array.from(this.agents.values()); }

  /** 智能推荐 — 根据任务描述推荐最合适的 Agent（可配置评分权重）。
   * 默认策略：多阶段加权评分
   * 1. 精确匹配：task 中是否包含 skills 列表中的关键词 (weight: 0.4)
   * 2. 标签匹配：metadata.tags 与 task 的交集计数 (weight: 0.3)
   * 3. 文本相似度：description + skills 与 task 的 embedding 余弦距离（V2 引入）(weight: 0.3) */
  recommend(task: string, config?: RecommendConfig): RecommendedAgent[] { /* ... */ return []; }

  /** 卸载一个 Agent（Plugin unload 时调用） */
  unregister(id: string): void { this.agents.delete(id); }
}

interface RecommendedAgent {
  agent: Agent;
  score: number;               // 匹配度评分 (0-1)
  reason: string;              // 推荐理由（给 Orchestrator 参考）
}

/** M3：Agent 推荐的可选权重配置，默认 { keywordWeight: 0.4, tagWeight: 0.3, embeddingWeight: 0.3 } */
interface RecommendConfig {
  keywordWeight?: number;      // 关键词匹配权重 (default: 0.4)
  tagWeight?: number;          // 标签匹配权重 (default: 0.3)
  embeddingWeight?: number;    // embedding 相似度权重 (default: 0.3)
}
```

### 2.6 Universal Agent Loop — Agent 执行引擎 (v4 重构)

**Universal Loop 不再是"运行配置的函数"，而是"驱动一个完整 Agent 实例的执行循环"：**

```typescript
/** 
 * Universal Agent Loop —— 驱动任意 Agent 执行的通用循环。
 * 所有 Agent（包括 Orchestrator）都通过此循环执行。
 */
/** Token 预算阈值 — 根据模型上下文窗口动态计算，避免硬编码。默认取 maxTokens 的 80% */
function calculateTokenBudget(maxTokens: number): number {
  return Math.floor(maxTokens * 0.8);
}

/** 递归委派深度追踪 — 由 runAgentLoop 内部自动检查上限 */
async function runAgentLoop(config: AgentRunConfig): Promise<AgentResult> {
  const { agent, messages, memory, maxIterations = 20 } = config;
  
  // 在循环开始时检查委派深度，防止无限递归
  // delegationDepth 始终从 context（ToolExecutionContext）读取
  // 实际上限可从 PlatformConfig.delegation.maxDepth 覆盖，未配置时默认 DEFAULT_MAX_DELEGATION_DEPTH(5)
  // H7：context 可选，内部默认空对象防止 undefined 访问
  const ctx = config.context ?? {};
  const depth = ctx.delegationDepth ?? 0;
  if (depth >= DEFAULT_MAX_DELEGATION_DEPTH) {
    return { status: 'failed', agentId: agent.id, error: `Delegation depth limit reached (${DEFAULT_MAX_DELEGATION_DEPTH})` };
  }

  let iteration = 0;
  let totalTokens = 0;   // Token 用量累计
  /** 连续 compact() 返回 0 的计数器 — 防止反复调用无意义的 compaction */
  let consecutiveCompactFailures = 0;

  while (iteration < maxIterations) {
    // Token 预算检查：超过阈值时压缩 STM 释放空间
    const budget = calculateTokenBudget(agent.maxTokens ?? 128000);
    if (totalTokens > budget) {
      const freed = await memory.compact();
      totalTokens -= freed;

      // compact() 返回 0 表示无法进一步压缩，连续失败超过 3 次则放弃
      if (freed === 0) {
        consecutiveCompactFailures++;
        if (consecutiveCompactFailures >= 3) {
          // Token 预算超限但 STM 无法再压缩 — 让 LLM 自行处理（可能返回短答案）或在下一次迭代中达到 maxIterations
          break;
        }
      } else {
        consecutiveCompactFailures = 0;  // 成功释放 token，重置计数器
      }
    }

    // Hook: LLM 调用前（Skill 注入、工具动态增减）
    const llmCtx = await hookBus.emit('llm:beforeCall', {
      messages, tools, agentId: agent.id, agentName: agent.name
    });

    let response: ChatResponse;
    try {
      // ⚠️ V1 注意：V4 Loop 使用 llm.complete(options: {messages, tools})，但 V1 Adapter 签名是 complete(messages: ChatMessage[], tools?: ToolDefinition[])。
      // 实现 V1 时请用位置参数调用，不要传 options 对象。（详见 architecture-v1.md §3.1）
      response = await llm.complete({   // LLM API 调用失败保护
        messages: llmCtx.modifiedMessages ?? messages,
        // 优先使用 Hook 修改后的工具列表，否则回退到 config.tools 或 registry（V1 通过 registry 获取）
        tools: llmCtx.modifiedTools?.map(t => t.getTools()).flat() ?? config.tools?.map(t => t.getTools()).flat() ?? []
      });
    } catch (err) {
      await hookBus.emit('error:caught', {
        error: err as Error, meta: { agentId: agent.id, phase: 'llm_call' }
      });
      return { status: 'failed', agentId: agent.id, error: `LLM API call failed: ${(err as Error).message}` };
    }

    // 检查 Hook 执行是否有错误
    if (llmCtx.hasErrors) {
      await hookBus.emit('error:caught', {
        error: new Error('One or more hooks failed during llm:beforeCall'),
        meta: { agentId: agent.id, phase: 'hook_error' }
      });
    }

    // 无工具调用时，先 emit afterLoop 再返回
    if (!response.message.toolCalls?.length) {
      await hookBus.emit('agent:afterLoop', { 
        taskId: ctx.traceId ?? 'unknown', 
        result: { status: 'completed', output: response.message.content, agentId: agent.id }
      });
      return { status: 'completed', output: response.message.content, agentId: agent.id };
    }

    // Tool 执行（文件级锁：同文件操作串行，不同文件并行）
    const results = await executeToolCallsWithFileLock(
      response.message.toolCalls,
      ctx as ToolExecutionContext
    );

    // tool:afterExecute Hook 已在 ToolRegistry.execute() 内部对每个 tool call emit，此处不再重复 emit

    messages.push(...results);
    totalTokens += response.usage.totalTokens;   // 累计 token
    
    iteration++;
  }

  // cancelled 状态由外部触发，通过 AbortController 或共享 flag 检测
  return { status: 'max_iterations_reached', agentId: agent.id };
}

interface AgentRunConfig {
  agent: Agent;   // Agent 实例（不是配置！）
  messages: ChatMessage[];                 // 初始消息列表
  memory: ShortTermMemory;                 // STM
  context?: Partial<ToolExecutionContext>;  // delegationDepth 从此读取
  maxIterations?: number;                  // 最大迭代次数
  tools?: ToolHandler[];                   // V4 Hook 场景：可动态增减的工具处理器列表（由 llm:beforeCall Hook 修改）；V1 不使用此字段，直接从 registry 获取工具定义
}

interface AgentResult {
  status: 'completed' | 'max_iterations_reached' | 'failed' | 'cancelled';
  output?: string;                         // Agent 的最终输出（失败时可能为空）
  agentId: string;                         // 哪个 Agent 执行的
  error?: string;                          // 失败原因
  usage?: TokenUsage;                      // token 用量统计
}

/** 从文件路径中提取规范化的绝对路径，用于文件级锁分组。@deprecated V2+ 请使用 extractFilePathAsync */
function extractFilePath(rawPath: unknown): string | null {
  if (typeof rawPath !== 'string' || !rawPath) return null;
  // 规范化路径：resolve 到绝对路径并去除尾部斜杠
  const pathModule = require('path');   // CJS 环境中同步可用
  return pathModule.resolve(rawPath);
}

/** ESM 兼容版本 — 在纯 ESM 模块中使用动态 import */
export async function extractFilePathAsync(rawPath: unknown): Promise<string | null> {
  if (typeof rawPath !== 'string' || !rawPath) return null;
  try {
    const { resolve } = await import('path');  // ESM 安全的路径解析
    return resolve(rawPath);
  } catch {
    // Node.js 以外环境（如浏览器）无 path 模块，fallback 返回原始值
    return rawPath.startsWith('/') || rawPath.startsWith('.') ? rawPath : null;
  }
}

/** 从 ToolCall.arguments（unknown）中提取路径字段 */
function safeExtractPath(call: ToolCall): string | null {
  const args = call.arguments as Record<string, unknown> | undefined;
  return args && typeof args.path === 'string' ? extractFilePath(args.path) : null;
}

/**
 * 文件级锁：按文件路径+操作类型分组工具调用，同文件的写操作串行执行避免竞态。
 */

const MAX_CONCURRENT_TOOL_CALLS = 20;

async function executeToolCallsWithFileLock(
  calls: ToolCall[],
  ctx: ToolExecutionContext,
  maxConcurrency: number = MAX_CONCURRENT_TOOL_CALLS,
  registry?: ToolRegistry   // V1 不需要文件级锁，可传 undefined；V4 传入共享 registry 用于执行
): Promise<ToolResult[]> {
  // 分组时保留原始索引
  const writeOps = new Set(['write_file', 'edit_file', 'delete_file']);
  const indexedByGroup = new Map<string, Array<{ index: number; call: ToolCall }>>();
  for (let i = 0; i < calls.length; i++) {
    const filePath = safeExtractPath(calls[i]);
    const isWriteOp = writeOps.has(calls[i].name);
    const groupKey = filePath ? `${filePath}:${isWriteOp ? 'w' : 'r'}` : calls[i].name;
    if (!indexedByGroup.has(groupKey)) indexedByGroup.set(groupKey, []);
    indexedByGroup.get(groupKey)!.push({ index: i, call: calls[i] });
  }

  // 分组后按并发上限分批执行
  const groups = Array.from(indexedByGroup.entries());
  const results: ToolResult[] = new Array(calls.length);

  for (let i = 0; i < groups.length; i += maxConcurrency) {
    const batch = groups.slice(i, i + maxConcurrency);
    await Promise.all(
      batch.map(async ([group, indexedCalls]) => {
        for (const { index, call } of indexedCalls) {
          results[index] = await registry!.execute(call, ctx);
        }
      })
    );
  }

  return results;
}
```

---

## 三、扩展系统 (Plugin + Skill + Hook)

### 3.1 Plugin System — 代码级扩展

**一个 Package = 一个 Plugin，可声明任意组合的能力：**

```typescript
interface PluginManifest {
  id: string;                    // "tdd", "security"
  name: string;
  version: { major: number; minor: number; patch: number };
  dependsOn?: Record<string, VersionRange>;   // 依赖其他插件（必须）
  optionalDependsOn?: Record<string, VersionRange>;  // 可选依赖
  main: string;                  // 入口模块
  license: string;               // SPDX 许可证标识
  
  /** 
   * 安全声明：插件需要哪些权限？用户安装/加载时可见。
   */
  permissions?: Permission[];

  /** 
   * 本插件定义的 Agent（可选）。
   * Plugin 可以定义新的 Agent 类型，注册到 AgentRegistry。
   */
  definesAgents?: string[];      // 本插件定义了哪些 Agent ID
}

interface Permission {
  type: 'read_file' | 'write_file' | 'exec_command' | 'network_access';
  scope?: string;                // 如 "project_root/**", "*" (全部)
  description: string;           // 人类可读说明
}

interface Plugin {
  readonly manifest: PluginManifest;

  onLoad(context: PluginContext): Promise<void>;    // 加载时调用（async）
  onUnload?(context: PluginContext, snapshot?: unknown): Promise<unknown>;
  onRestore?(context: PluginContext, snapshot?: unknown): Promise<void>;

  /** 所有可选方法统一返回空集合而非 undefined */
  getTools?(): Promise<ToolHandler[]>;              // 未实现时返回 []
  getSkillIds?(): Promise<string[]>;                // 声明提供的 Skill（文本包）
  getHooks?(): Promise<HookRegistration[]>;         // 注册 Hook 拦截器

  defineAgents?(): Promise<Agent[]>;                 // 返回本插件定义的 Agent 列表
}

interface PluginContext {
  hooks: HookRegistrar;              // 注册 Hook
  skills: SkillRegistryAccess;       // 访问 Skill Registry
  
  /** Agent 注册中心 —— Plugin 通过此 API 定义新 Agent */
  agents: AgentRegistry;             // v4 新增
  
  logger: PluginLogger;              // 插件作用域的日志记录器
  config: Readonly<PlatformConfig>;  // 只读平台配置
  
  /** 注册自定义 Skill 模板变量 */
  registerSkillVariable(name: string, factory: (session: Session) => unknown): void;
  
  onReady(): Promise<void>;          // 标记插件初始化完成
}

interface PluginLogger {
  info(msg: string, meta?: Record<string, unknown>): void;
  warn(msg: string, meta?: Record<string, unknown>): void;
  error(msg: string, meta?: Record<string, unknown>): void;
  debug(msg: string, meta?: Record<string, unknown>): void;
}

/**
 * Plugin Manager — 生命周期管理、依赖解析、热重载。
 */
class PluginManager {
  discover(sources: PluginSource[]): Promise<PluginManifest[]>;
  load(manifests: PluginManifest[]): Promise<Map<string, Plugin>>;
  /** 
   * 热重载：新版本替换旧版本。活跃会话继续使用旧版 Handler（直到会话结束）。
   * 并发安全：新旧 handler 通过 version tag 区分，Hook Bus 按注册时版本号路由。
   */
  hotReload(id: string): Promise<Plugin>;
  get(id: string): Plugin;
  validateDependencies(manifests: PluginManifest[]): DependencyError[];
  unloadAll(): Promise<void>;
}

type PluginSource = 
  | { type: 'directory'; path: string }
  | { type: 'registry'; name: string; apiKey?: string }
  | { type: 'git'; url: string; ref?: string };
```

### 3.2 Skill System — 知识注入层

**Skill 是文本包，不是可执行代码。** 它通过渲染模板注入系统提示词来引导 Agent 行为。

```typescript
/** PluginVersion — 统一版本类型，PluginManifest / SkillManifest 共用 */
type PluginVersion = { major: number; minor: number; patch: number };

interface SkillManifest {
  id: string;                    // "tdd-workflow"
  name: string;
  version: PluginVersion;        // 与 PluginManifest.version 同类型
  description: string;
  providerPluginId: string;      // 哪个插件提供（归属）
  tags: string[];                // ["testing", "workflow"]
  category: SkillCategory;       // development | security | operations | ...
  
  requiresTools?: string[];       // 需要的工具列表（激活时自动注入到可用工具集）
  activationMode: 'manual' | 'auto' | 'always';
  autoRules?: AutoActivationRule[];
}

type SkillCategory = 
  | 'development'     // 编码工作流、测试、重构
  | 'security'        // 安全扫描、代码审查
  | 'operations'      // 部署、监控、调试
  | 'communication'   // 文档、PR 描述、Changelog
  | 'research'        // 信息收集、分析
  | 'custom';         // 用户自定义

interface AutoActivationRule {
  matchAgentType?: string[];       // 匹配 Agent ID
  matchFilePatterns?: string[];    // 匹配文件模式
  matchKeywords?: string[];        // 匹配用户消息关键词
}

interface SkillBundle {
  manifest: SkillManifest;

  /** 安全说明：模板引擎必须使用沙箱模式，只允许访问白名单变量。
   * 禁止直接注入 LTM/Vector 等不可信数据到模板中，防止 prompt injection。
   * 安全限制：禁用 {{#with}}, {{#each}}, {{#if}}、三重大括号输出原始 HTML、自定义 helper */

  /**
   * 系统提示词模板。使用 Handlebars-style {{variables}} 语法，
   * 在激活时由 SessionContext 注入变量值后渲染为纯文本。
   * 
   * 内置变量（Platform 自动注册）：
   *   {{agentId}}       - 当前 Agent ID
   *   {{projectRoot}}   - 项目根目录绝对路径
   *   {{fileCount}}     - 作用域内文件数量
   *   {{language}}      - 检测到的主要编程语言
   */
  systemPromptTemplate: string;

  additionalTools?: ToolDefinition[];
  examples?: SkillExample[];            // Few-shot 示例

  /** Skill 是纯文本包，不包含可执行代码。
   * 如需响应后处理，Plugin 应通过 Hook Bus 注册 llm:afterResponse Handler */
}

interface SkillExample {
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
  toolResults?: ToolResult[];
}

/** Skill 模板变量注册表 — 内置变量使用白名单 */
class SkillVariablesRegistry {
  /** 内置白名单变量 — 由 Platform 自动注册，不可被覆盖 */
  private readonly builtinWhitelist = new Set(['agentId', 'projectRoot', 'fileCount', 'language']);

  register(name: string, factory: (session: Session) => unknown): void {
    // S17：自定义变量名不得与内置白名单冲突
    if (this.builtinWhitelist.has(name)) {
      throw new Error(`Cannot override builtin skill variable: ${name}`);
    }
    // Git/Registry 来源插件注册的变量标记为 untrusted，模板引擎应对输出做 HTML/Markdown 转义。
  }

  resolveAll(session: Session): Record<string, unknown>;
}

/** 
 * Skill Registry — 发现、加载、激活管理。
 */
class SkillRegistry {
  discover(sources: SkillSource[]): Promise<SkillManifest[]>;
  load(skillId: string): Promise<SkillBundle>;
  getActiveSkills(sessionId: string): Promise<SkillBundle[]>;
  buildSkillPrompt(sessionId: string, sessionContext: Session): Promise<string>;
  getActiveSkillTools(): ToolDefinition[];
  register(bundle: SkillBundle): void;
  unregister(skillId: string): void;
}

type SkillSource =
  | { type: 'directory'; path: string }
  | { type: 'registry'; name: string }
  | { type: 'git'; url: string; ref?: string };
```

### 3.3 Hook Mechanism — 运行时拦截

**Hook 是事件驱动的拦截点，每个 Hook 有优先级、错误隔离、可选的短路能力。**

```typescript
type HookEvent =
  // ── 会话生命周期 ──
  | 'session:start'        // { sessionId, agentId }
  | 'session:end'          // { sessionId }

  // ── Agent 循环 ──
  | 'agent:beforeLoop'     // 任务执行前
  | 'agent:afterLoop'      // 任务执行后
  | 'agent:beforeExecute'  // Agent 开始执行具体任务时

  // ── LLM 交互 ──
  | 'llm:beforeCall'       // 可修改 messages、tools
  | 'llm:afterResponse'    // 分析响应、注入警告

  // ── 工具执行 ──
  | 'tool:beforeExecute'   // 安全检查、前置验证。可设置 error/blockReason 阻断执行
  | 'tool:afterExecute'    // TDD 自动跑测试、审计日志

  // ── 记忆操作 ──
  | 'memory:beforeWrite'   // 写入前拦截（如敏感信息过滤）
  | 'memory:afterWrite'
  | 'memory:beforeRead'
  | 'memory:afterRead'

  // ── 错误处理 ──
  | 'error:caught'         // 任何未处理的平台级错误

type HookHandler<TCtx extends BaseHookContext = BaseHookContext> = 
  (ctx: TCtx) => void | Promise<void>;

/** Hook 执行深度上限 — 防止 memory:beforeWrite → write → beforeWrite 无限循环（默认 10）*/
const MAX_HOOK_DEPTH = 10;

/** 所有 Hook Context 的基础字段 */
interface BaseHookContext {
  sourcePluginId: string;   // 触发该事件的插件 ID
  traceId: string;          // 请求级追踪 ID
  timestamp: number;        // 事件发生时间戳
  /** 当前 Hook 调用链深度 — HookBus.emit() 自动递增，防止嵌套写入导致无限循环 */
  hookDepth?: number;       // 由 HookBus 内部管理，Hook Handler 不应手动修改
}

/** 各事件类型的专用 Context（扩展 BaseHookContext）── */

/** LLMCallContext — tools 字段是 ToolHandler[]，modifiedTools 也是 ToolHandler[]。
 * Hook 应修改 ToolHandler（增删工具），调用方负责将其转换为 ToolDefinition[] 传给 LLM。 */
interface LLMCallContext extends BaseHookContext {
  messages: ChatMessage[];
  tools: ToolHandler[];             // 当前可用的工具处理器列表
  agentId: string;
  agentName: string;                // Agent 名称
  /** Hook 可修改这些字段，emit() 返回后由调用方读取 */
  modifiedMessages?: ChatMessage[];
  /** Hook 直接修改 ToolHandler 列表（增/删/替换）*/
  modifiedTools?: ToolHandler[];    // 与 tools 同类型
}

interface ToolExecuteContext extends BaseHookContext {
  toolId: string;           // 工具 ID（如 "filesystem", "git"）
  toolCall: ToolCall;       // 完整的工具调用参数
  /** 执行上下文，由 ToolRegistry.execute() 传入 */
  context?: ToolExecutionContext;
  blocked?: boolean;        // Hook 设置此字段阻断执行
  blockReason?: string;     // 阻断原因
  error?: Error;            // Hook 设置此字段标记安全拦截
}

interface LLMResponseContext extends BaseHookContext {
  response: ChatResponse;   // LLM 返回结果
  /** 追加系统级消息（如安全警告）到对话历史 */
  appendWarning: (msg: string) => void;
}

interface MemoryWriteContext extends BaseHookContext {
  key?: string;             // 写入的键（可选）
  content: string;          // 原始内容
  /** Hook 可设置此字段过滤内容 */
  modifiedContent?: string;
  blocked?: boolean;        // Hook 设置此字段阻断写入
  blockReason?: string;     // 阻断原因（如检测到敏感信息）
}

interface ToolResultContext extends BaseHookContext {
  results: ToolResult[];    // 工具执行结果列表
}

/** Hook Event → Context 映射表，确保 emit 时类型匹配 */
type HookEventMap = {
  'session:start': BaseHookContext & { sessionId: string; agentId: string };
  'session:end': BaseHookContext & { sessionId: string };
  'agent:beforeLoop': BaseHookContext & { taskId: string };
  'agent:afterLoop': BaseHookContext & { taskId: string; result?: AgentResult };
  'agent:beforeExecute': BaseHookContext & { agentId: string; task: string };
  'llm:beforeCall': LLMCallContext;
  'llm:afterResponse': LLMResponseContext;
  'tool:beforeExecute': ToolExecuteContext;
  'tool:afterExecute': ToolResultContext;
  'memory:beforeWrite': MemoryWriteContext;    // S16：支持 modifiedContent 过滤和 blocked 阻断
  'memory:afterWrite': BaseHookContext & { key?: string };
  'memory:beforeRead': BaseHookContext & { key?: string };
  'memory:afterRead': BaseHookContext & { results?: unknown[] };
  'error:caught': BaseHookContext & { error: Error; meta?: Record<string, unknown> }; // meta 避免与 ToolExecutionContext 重名
};

interface HookRegistration<TEvent extends HookEvent = HookEvent> {
  event: TEvent | TEvent[];
  handler: HookHandler<Extract<HookEventMap[TEvent], BaseHookContext>>;
  priority?: number;                    // 越小越先执行。默认 100
  shortCircuit?: boolean;              // true = 返回非空值时停止后续 Handler
  once?: boolean;                      // 只触发一次后自动注销
}

/** 
 * Hook Bus — 事件路由引擎。
 */
class HookBus {
  on<TEvent extends HookEvent>(registration: HookRegistration<TEvent>): UnregisterFn;   // 注册全局 Hook（所有 Session 生效）
  /** onSession 注册的 Hook 仅在 sessionId 内触发。
   * clearSession(sessionId) 是推荐的清理方式。 */
  onSession(sessionId: string, registration: HookRegistration<HookEvent>): UnregisterFn;
  /** emit 返回执行结果 + 可能被 Hook 修改后的 context（供 llm:beforeCall 等读取）*/
  emit<TEvent extends HookEvent>(event: TEvent, ctx: HookEventMap[TEvent]): Promise<HookEmitResult<HookEventMap[TEvent]>>;
  off(sessionId?: string): void;   // sessionId? 时仅注销全局 Hook；注销 onSession 注册的请用 clearSession()
  clearSession(sessionId: string): void;
  listHooks(filter?: { event?: HookEvent; pluginId?: string }): RegisteredHook[];
}

interface HookExecutionResult {
  durationMs: number;
  executions: HookHandlerResult[];
  hasErrors: boolean;
  stats: { success: number; failure: number; skipped: number };
  blocked?: boolean;
  blockReason?: string;
}

/** M5：emit() 的包装返回类型 — 将执行结果与事件特定 context 分离，避免交叉类型 */
interface HookEmitResult<TContext extends BaseHookContext> {
  result: HookExecutionResult;   // stats, duration, errors
  context: TContext;             // 事件特定字段（modifiedMessages, modifiedTools 等）
}

interface HookHandlerResult {
  pluginId: string;
  priority: number;
  success: boolean;
  durationMs: number;
  error?: Error;
}

type UnregisterFn = () => void;
```

**Hook 执行模型：**

```
llm:beforeCall 事件触发 (priority=0,10,50,100,200)
  │
  ├─ [p=0]   Platform Core: inject system prompt        ✓
  ├─ [p=10]   Security Plugin: add security context      ✓
  ├─ [p=50]   Skill Registry: render skill templates     ✓
  ├─ [p=100]  TDD Plugin: inject TDD reminder            ✓
  └─ [p=200]  User Hook: custom logging                  ✓
  
结果: { durationMs: 45, success: 5, failure: 0 }
```

### 3.4 组合示例：多 Agent 协作流程（v4 核心场景）

**用户请求 → Orchestrator Agent 分解任务 → 委派给专业 Agent：**

```
用户说: "用 TDD 方式实现排序函数，并审查代码质量"
  │
  ▼
Orchestrator Agent (接收请求)
  │
  ├─ LLM 调用 → 识别到两个子任务：
  │   1. "用 TDD 实现 quickSort"    → 委派给 Coding Agent
  │   2. "审查排序模块代码质量"      → 委派给 Review Agent
  │
  ▼ delegate_to_agent(coding-agent, "用 TDD 实现 quickSort")
     │
     ├─ Coding Agent (接收任务)
     │   ├── Skill: tdd-workflow 自动激活
     │   ├── Hook: tool:afterExecute → 自动跑测试
     │   └── LLM ↔ Tools Loop:
     │       RED: write test_quickSort.ts → run_tests → FAIL ✓
     │       GREEN: write quickSort.ts → run_tests → PASS ✓
     │       REFACTOR: clean up code → run_tests → PASS ✓
     │
  ▼ delegate_to_agent(review-agent, "审查排序模块代码质量")
     │
     ├─ Review Agent (接收任务)
     │   ├── Skill: owasp-security-review 自动激活
     │   └── LLM ↔ Tools Loop:
     │       readFile(quickSort.ts) → readFile(test_quickSort.ts)
     │       git_diff → analyze_patterns
     │       output: "代码质量良好，建议增加边界条件测试"
     │
  ▼ collect_result() → 汇总两个 Agent 的输出
  │
  ▼ Orchestrator 返回给用户：
    "✅ quickSort 已实现并通过测试 (TDD)
     📋 Review 结果: 代码质量良好，建议增加边界条件测试"
```

---

## 四、安全策略

### 4.1 纵深防御模型

```
Layer 1: 权限上下文 (ToolExecutionContext)     — 每个会话独立的权限边界
Layer 2: Hook 前置拦截 (tool:beforeExecute)     — 危险操作实时阻断
Layer 3: 命令白名单/黑名单                       — 基于模式的过滤
Layer 4: 文件访问控制 (chroot / sandbox path)    — 限制可操作的文件范围
Layer 5: 审计日志 (所有工具调用的完整记录)         — 事后追溯
```

### 4.2 具体安全措施

| 威胁 | 防御层 | 实现方式 |
|------|--------|----------|
| **命令注入** | Hook + 白名单 | `tool:beforeExecute` 检查命令模式；只允许预定义命令列表 |
| **文件越权访问** | 权限上下文 | 每个会话有 `allowedPaths`，工具执行前校验路径在允许的目录内 |
| **恶意代码执行** | 沙箱隔离 | V2+ 使用容器隔离；V1 限制 shell 命令为白名单子集 |
| **Secret 泄露到 LLM** | Hook + 过滤 | `llm:beforeCall` 扫描 messages，移除疑似密钥的模式 |
| **LLM 输出注入 Secret** | Hook | `llm:afterResponse` 扫描响应内容，发现密钥则警告并阻止写入文件 |
| **资源耗尽 (无限循环)** | Orchestrator | `maxIterations` 限制 Agent Loop 轮次；单工具调用超时；Token 预算追踪 |
| **Prompt Injection** | 输入隔离 | 用户输入的文本与系统提示词严格分离，不直接拼接 |
| **并行写竞态** | Orchestrator | 文件级锁：同文件操作串行，不同文件并行（见 2.6 节） |

### 4.3 Plugin 安全声明与权限模型

```typescript
// Permission 已在 Section 3.1 定义。此处直接复用，详见 ADR-009。

// Security Plugin — tool:beforeExecute 前置检查（阻断机制闭环）
class SecurityPlugin implements Plugin {
  async onLoad(ctx: PluginContext): Promise<void> {
    ctx.hooks.on('tool:beforeExecute', this._validateSafety, { priority: 10 });
    ctx.hooks.on('llm:afterResponse', this._scanForSecrets);
    await ctx.onReady();
  }

  private _validateSafety = async (ctx: ToolExecuteContext): Promise<void> => {
    const dangerousPatterns = [/rm\s+-rf/, /\bexec\(/, /eval\(/, /\.env/];
    
    for (const pattern of dangerousPatterns) {
      if (pattern.test(JSON.stringify(ctx.toolCall.arguments))) {
        ctx.error = new SecurityError(`Blocked: ${pattern}`);
        return;   // Hook 链继续（其他安全插件也能看到），但工具不会执行
      }
    }
  };

  private _scanForSecrets = async (ctx: LLMResponseContext): Promise<void> => {
    if (ctx.response?.content) {
      const findings = scanForPatterns(ctx.response.content, SECRET_PATTERNS);
      if (findings.length > 0) {
        ctx.appendWarning(`[Security Warning: ${findings.length} potential secrets detected.]`);
      }
    }
  };
}
```

### 4.4 Plugin 安装安全

| 来源 | 验证方式 | 风险等级 |
|------|----------|---------|
| 本地目录 (`directory`) | 用户自行管理，无额外验证 | 中（用户自己负责） |
| Registry (`registry`) | 签名验证 + 插件版本审核 | 低 |
| Git URL (`git`) | 用户确认 + 权限声明预览 | 中-高（需人工审查代码） |

---

## 五、错误处理策略

### 5.1 错误分类与响应

| 级别 | 类型 | 示例 | 处理方式 |
|------|------|------|----------|
| **P0 - Fatal** | 平台崩溃 | OOM, 数据库连接丢失 | 重启服务，通知用户，保留会话状态 |
| **P1 - Critical** | 核心功能失败 | LLM API 超时、工具执行权限不足 | 降级/重试，告知用户具体原因 |
| **P2 - Warning** | 非核心失败 | Hook 执行异常、记忆写入失败 | 记录日志，继续执行，不中断流程 |
| **P3 - Info** | 可忽略 | 缓存未命中、可选功能不可用 | 仅日志记录 |

### 5.2 关键组件的错误处理

```typescript
// LLM Adapter — Circuit Breaker（三态：closed → open → half-open → closed）+ Fallback Chain
type CircuitState = 'closed' | 'open' | 'halfOpen';

class LLMAdapter {
  private failureCount = 0;
  private state: CircuitState = 'closed';
  private fallbackIndex = 0;                   // H1：用索引替代 shift()，避免破坏性删除
  private readonly circuitThreshold = 3;       // N 次连续失败后打开熔断器
  private readonly recoveryTimeoutMs = 30_000; // 30s 后进入 half-open 试探恢复
  
  async complete(options: ChatOptions): Promise<ChatResponse> {
    // open 状态：直接走 fallback，避免无效请求
    if (this.state === 'open') {
      throw new CircuitOpenError('Circuit open, routing to fallback');
    }

    try {
      const response = await this._callLLM(options);
      
      if (this.state === 'halfOpen') {
        // half-open 成功 → 恢复正常（closed），重置所有状态
        this.state = 'closed';
        this.failureCount = 0;
        this.fallbackIndex = 0;                  // H1：恢复时重置 fallback 索引
      } else if (this.state === 'closed') {
        // closed 状态下成功 → 重置计数器
        this.failureCount = 0;
      }
      
      return response;
    } catch (err) {
      this.failureCount++;
      
      if (this.failureCount >= this.circuitThreshold && this.state !== 'open') {
        // 连续失败达到阈值 → 打开熔断器，启动恢复计时
        this.state = 'open';
        setTimeout(() => { this.state = 'halfOpen'; }, this.recoveryTimeoutMs);
      }
      
      // 在熔断器打开前，尝试 fallback chain（仅 closed/half-open 状态能走到这里）— H1：用索引访问而非 shift()
      if (this.fallbackIndex < this.fallbackModels.length) {
        const fallback = this.fallbackModels[this.fallbackIndex++];
        return await this._callWithModel(fallback, options);
      }
      
      throw err;   // 所有策略用尽，向上传播
    }
  }
}

interface RetryPolicy { maxRetries: number; baseBackoffMs: number; }
```

### 5.3 错误传播路径

```
用户请求 → Platform Session Manager
  │
  ├── P0 Fatal ──► 平台日志 + 通知 + 尝试恢复 ──► 返回 "服务不可用"
  │
  ├── P1 Critical ──► 向上传播到 Orchestrator
  │     ├── LLM 失败 → Circuit Breaker + Fallback Chain → 仍失败 → 返回 "LLM 暂时不可用"
  │     ├── Agent 委派失败 → Retry → Fallback Agent → 仍失败 → 返回错误信息
  │     └── Tool 执行失败 → Hook error:caught → 包装为 isError:true → 给 LLM 看
  │
  ├── P2 Warning ──► Hook Bus 记录 + error:caught 事件
  │     └─→ 不影响主流程，用户不可见（除非查看日志）
  │
  └── P3 Info ──► 仅日志
```

---

## 六、平台能力与运维

### 6.1 分层测试金字塔

```
         /\ E2E (5-10%)
        /--\
       /----\ Integration (15-20%)
      /------\
     /--------\ Unit (70-80%)
    /----------\
```

### 6.2 各层测试范围

| 层级 | 覆盖范围 | 示例 | 工具 |
|------|----------|------|------|
| **Unit** | 单个包内的函数/类 | `ShortTermMemory.add()` 正确管理 Ring Buffer；`HookBus.emit()` 按优先级排序执行 | Vitest + Mock LLM |
| **Integration** | 跨包协作 | Orchestrator Agent 委派 Coding Agent → Tool Registry → Memory Store 的完整链路 | Test Container (真实 DB) |
| **E2E** | 端到端用户场景 | 多 Agent 协作完成 "用 TDD 实现排序函数并审查" | LLM Replay（录制回放） |

### 6.3 Mock 策略

```typescript
// Unit Test: Mock LLM Adapter
const mockLLM: Partial<LLMAdapter> = {
  complete: vi.fn().mockResolvedValue({
    message: { role: 'assistant', content: '', toolCalls: [...] },
    usage: { promptTokens: 100, completionTokens: 50, totalTokens: 150 },
    finishReason: 'tool_calls',
  }),
};

// Integration Test: Mock Tool Execution (不真正执行 Shell)
const mockToolRegistry: Partial<ToolRegistry> = {
  execute: vi.fn().mockResolvedValue({ content: 'echo "hello"', isError: false }),
};

// E2E Test: LLM Replay — 录制真实 API 响应，测试时回放
```

### 6.4 契约测试 (Contract Testing)

**LLM Adapter 的契约测试确保所有 Provider 实现行为一致：**

```typescript
// llm-adapter/shared.spec.ts — 所有 adapter 共享的测试套件
describe('LLMAdapter Contract', () => {
  it('returns structured output matching ChatResponse schema', () => {});
  it('stream() yields chunks with done=true on final chunk', () => {});
  it('completeWithSchema() validates and returns typed result', () => {});
  it('capabilities.report matches actual API response', () => {});
});

// anthropic.spec.ts, openai.spec.ts ... 各自 import 运行同一套测试
```

### 6.5 Hook/Skill/Plugin/Agent 专项测试

```typescript
describe('HookBus', () => {
  it('executes hooks in priority order (lower first)', async () => {});
  it('isolates errors — one failing hook does not stop the chain', async () => {});
  it('shortCircuit=true stops further execution on non-empty return', async () => {});
  it('once=true auto-unregisters after first fire', async () => {});
  it('session-scoped hooks do not leak to other sessions', async () => {});
  it('clearSession() removes all session-specific hooks', async () => {});
  it('prevents infinite loops via write depth limit (max 10)', async () => {});
});

describe('Plugin Lifecycle', () => {
  it('loads plugins in dependency order (topological sort)', async () => {});
  it('rejects incompatible version ranges', async () => {});
  it('hotReload preserves other loaded plugins and passes state snapshot', async () => {});
});

describe('Skill Activation', () => {
  it('auto-activates when agent id matches rules', async () => {});
  it('renders {{variables}} with session context from VariablesRegistry', async () => {});
  it('merges tool definitions from active skills', async () => {});
});

describe('Agent Registry', () => {
  it('registers agents and returns them by id', async () => {});
  it('recommends agents based on task description scoring', async () => {});
  it('unregistered agent is removed from list()', async () => {});
});

describe('Orchestrator Agent — Multi-Agent Delegation', () => {
  it('delegates subtasks to correct agents by id', async () => {});
  it('collects results from parallel agent executions', async () => {});
  it('falls back to alternative agent when primary fails', async () => {});
});

describe('Tool Registry — File Locking', () => {
  it('serializes writes to the same file across parallel calls', async () => {});
  it('executes operations on different files in parallel', async () => {});
});
```

---

### 6.6 可观测性 (Observability)

所有核心组件暴露结构化指标和追踪，支持接入 Prometheus/Grafana、OpenTelemetry 等标准可观测性栈。

#### 6.6.1 指标分类

| 类别 | 指标名 | 类型 | 说明 |
|------|--------|------|------|
| **LLM** | `agent_llm_call_duration_seconds` | Histogram | LLM API 调用延迟（分模型标签） |
| **LLM** | `agent_llm_calls_total` | Counter | LLM 调用次数（标签：model, status） |
| **Token** | `agent_token_usage_total` | Counter | Token 用量累计（标签：prompt/completion） |
| **Agent** | `agent_loop_iterations_total` | Counter | Agent Loop 迭代次数（标签：agent_id） |
| **Agent** | `agent_delegation_depth_histogram` | Histogram | 委派深度分布 |
| **Tool** | `agent_tool_executions_total` | Counter | 工具执行次数（标签：tool_id, success/error） |
| **Tool** | `agent_tool_duration_seconds` | Histogram | 工具执行延迟 |
| **Hook** | `hook_execution_duration_seconds` | Histogram | Hook 处理延迟（标签：event, plugin_id） |
| **Hook** | `hook_failures_total` | Counter | Hook 失败次数 |
| **Memory** | `memory_compact_count_total` | Counter | STM 压缩次数 |
| **Plugin** | `plugin_hot_reload_duration_seconds` | Histogram | 热重载耗时 |

#### 6.6.2 Tracing

```typescript
// 所有核心操作自动携带 traceId，形成完整的调用链追踪
interface TraceSpan {
  traceId: string;       // 全局唯一请求级追踪 ID
  spanId: string;        // 当前操作唯一 ID
  parentId?: string;     // 父 Span ID（嵌套关系）
  name: string;          // 操作名称，如 "llm.complete", "tool.execute", "agent.delegation"
  attributes: Record<string, unknown>;  // 标签（model, toolId, agentId...）
  durationMs?: number;   // 操作耗时
  status: 'ok' | 'error' | 'cancelled';
}

// HookBus 自动在每次 emit 时创建 Span，形成 Hook 执行链追踪
// AgentLoop 在每次迭代时创建父 Span，子操作（LLM call, tool execute）创建子 Span
```

#### 6.6.3 日志规范

- **结构化 JSON**：所有日志输出为 JSON 格式，包含 `timestamp`, `level`, `traceId`, `agentId`, `sessionId`
- **日志级别映射**：
  - `ERROR`：P0/P1 错误（LLM 持续失败、工具执行异常）
  - `WARN`：P2 警告（Hook 执行超时、记忆写入失败）
  - `INFO`：关键流程节点（Session 创建/结束、Agent 委派、Plugin 加载）
  - `DEBUG`：详细调试信息（消息内容、Token 用量明细）

#### 6.6.4 集成方式

```typescript
// 平台启动时注册可观测性后端
platform.use(observability({
  metrics: new PrometheusExporter(),   // Prometheus 指标导出
  tracing: new OpenTelemetryTracer(),  // OpenTelemetry 链路追踪
  logging: new StructuredLogger(),     // 结构化日志
}));

// Hook Bus 自动暴露为可观测性事件源，无需插件手动接入
```

---

### 6.7 并发与多用户支持 (Concurrency & Multi-user)

#### 6.7.1 V1 场景分析

CLI 是本地运行的 npm 包（`npm install -g`），V1 下核心并发挑战来自**同一个用户的多个终端窗口**：

| 场景 | 风险 | 处理方式 |
|------|------|---------|
| **同一用户开两个 CLI 终端，操作同一个项目** | SQLite 并发写入冲突；LTM/Vector Store 同时写导致数据损坏 | Session Manager 加文件锁（SQLite WAL 模式 + 行级锁）；STM 是进程内内存，天然隔离 |
| **同一 Agent Loop 并行执行多个工具调用** | 同文件写竞态 | ADR-015 文件级锁已覆盖 |
| **CLI 与未来 Web API 共存** | LTM/Vector Store 被本地和远程同时访问 | V2 迁移 PostgreSQL，V1 SQLite 仅限 CLI 本地使用 |

#### 6.7.2 Session Manager — 多终端并发安全

```typescript
/** Per-session async mutex — V2+ 需替换为 Redis 分布式锁 */
class AsyncMutex {
  private queue: Array<() => void> = [];
  private locked = false;

  async acquire(): Promise<() => void> {
    if (!this.locked) {
      this.locked = true;
      return () => { this.release(); };
    }
    return new Promise<() => void>((resolve) => {
      this.queue.push(() => {
        resolve(() => { this.release(); });
      });
    });
  }

  private release(): void {
    const next = this.queue.shift();
    if (next) {
      next();
    } else {
      this.locked = false;
    }
  }
}

class SessionManager {
  // V1: 单进程内用 Map + per-session async mutex 保证并发安全
  private sessions = new Map<string, Session>();
  /** 最大活跃会话数 — 超出时淘汰最早创建的 active session */
  private maxSessions = 50;

  /** per-session 异步锁 */
  private locks = new Map<string, AsyncMutex>();

  /** per-project 写锁 — 防止多终端同时创建 Session 时 LTM/SQLite 写入冲突 */
  private projectLocks = new Map<string, AsyncMutex>();

  private getLock(sessionId: string): AsyncMutex {
    if (!this.locks.has(sessionId)) this.locks.set(sessionId, new AsyncMutex());
    return this.locks.get(sessionId)!;
  }

  private getProjectLock(projectRoot: string): AsyncMutex {
    if (!this.projectLocks.has(projectRoot)) this.projectLocks.set(projectRoot, new AsyncMutex());
    return this.projectLocks.get(projectRoot)!;
  }

  /** M1 / L4：Session 创建加写锁，防止两个终端同时写入同一 LTM 文件时冲突 */
  async create(options: CreateSessionOptions): Promise<Session> {
    const release = await this.getProjectLock(options.projectRoot).acquire();
    try {
      // 超出 maxSessions 时淘汰最早创建的 active session（Map 迭代顺序保证）
    while (this.sessions.size >= this.maxSessions) {
      const oldestId = Array.from(this.sessions.keys()).at(-1);
      if (oldestId) {
        await this.end(oldestId);  // 触发正常清理流程（含 persistSessionSummary）
      } else {
        break;
      }
    }

    // SQLite 使用 WAL 模式 + PRAGMA journal_size_limit 控制并发写
    const session = new Session({ ... });

    await hookBus.emit('session:start', {
      sessionId: session.id, agentId: options.agentId
    });

    session.activeSkillIds = await skillRegistry.getActiveSkills(session.id)
      .then(skills => skills.map(s => s.manifest.id));

    this.sessions.set(session.id, session);
    return session;
    } finally {
      release();
    }
  }

  /** 清理时移除引用，释放内存。persistSessionSummary 内部使用 SQLite WAL 模式 + 参数化查询。
   * 多终端场景下 LTM 写入冲突由 memory-stm/ltm 层重试逻辑覆盖（最多 3 次指数退避）。 */
  async end(sessionId: string): Promise<void> {
    const release = await this.getLock(sessionId).acquire();
    try {
      await hookBus.emit('session:end', { sessionId });
      hookBus.clearSession(sessionId);

      const session = this.sessions.get(sessionId);
      if (session) {
        await persistSessionSummary(session);   // LTM 写入（SQLite WAL）
        this.sessions.delete(sessionId);        // 释放内存引用
      }
    } finally {
      release();
    }
  }

  /** 从 Failed 态恢复 — 使用 per-session 锁防止与 end() 竞态 */
  async recover(sessionId: string): Promise<Session> {
    const release = await this.getLock(sessionId).acquire();
    try {
      const session = this.sessions.get(sessionId);
      if (!session || session.status !== 'failed') {
        throw new Error(`Cannot recover session ${sessionId}: not in failed state`);
      }

      // 重建 STM（新 Ring Buffer）、重新激活 Skills、触发 session:start Hook
      session.stm = new ShortTermMemory();
      session.activeSkillIds = await skillRegistry.getActiveSkills(session.id)
        .then(skills => skills.map(s => s.manifest.id));
      session.status = 'active';

      await hookBus.emit('session:start', { sessionId, agentId: session.agentId });
      return session;
    } finally {
      release();
    }
  }

  get(id: string): Session | undefined {
    return this.sessions.get(id);
  }

  /** 列出当前用户所有活跃会话 */
  listByProject(projectRoot: string): Session[] {
    return Array.from(this.sessions.values())
      .filter(s => s.status === 'active' && s.projectRoot === projectRoot);
  }
}
```

#### 6.7.3 SQLite 并发限制与应对

| 操作 | SQLite WAL 模式表现 | V1 策略 |
|------|-------------------|--------|
| 多个读 + 一个写 | 读写不阻塞（WAL 允许并发读） | Session STM 写入、LTM KV 写入均可并发 |
| 多个写 | 最后一个成功，其他返回 `BUSY` | LTM 写入加重试逻辑（最多 3 次，指数退避 10ms/50ms/250ms） |
| Agent Memory 序列化 | Record<string, string> 原子写入 | 每次 save() 是单条 INSERT OR REPLACE，天然无冲突 |

#### 6.7.4 Agent Memory — V1 的"跨用户共享"边界

```typescript
// Agent Memory 跨会话共享，CLI 按 {agentId} 存储（V1 单用户）。

interface AgentMemoryStore {
  /** V1 按 agentId 存储（不分租户），V3 需要加 tenantId */
  save(agentId: string, data: AgentMemoryData): Promise<void>;
  load(agentId: string): Promise<AgentMemoryData | null>;
}

// V1：数据存储在 ~/.agent-platform/agents/{agentId}/memory.json
//     如果同一台机器有多个操作系统用户，通过目录权限隔离（OS 层面）
// V3：迁移到 PostgreSQL，加 tenant_id 列，应用层做租户隔离
```

---

### 6.8 部署架构 (Deployment Architecture)

#### 6.8.1 V1 — CLI 本地运行（无需服务器）

```
┌─────────────────────────────────────────────┐
│  用户机器                                    │
│  ┌───────────────────────────────────────┐  │
│  │  CLI (npm install -g)                 │  │
│  │  ├── Node.js 运行时                    │  │
│  │  ├── SQLite (文件存储, ~/.agent-platform/) │
│  │  └── LanceDB (本地向量索引)             │  │
│  └───────────────────────────────────────┘  │
│              │                                │
│         HTTPS 调用 LLM API                    │
│         (Anthropic/OpenAI/...)                │
└─────────────────────────────────────────────┘
```

| 组件 | 部署方式 | 限制 |
|------|---------|------|
| CLI | `npm install -g`，本地运行 | 单用户、单机；SQLite 并发写有限（WAL 模式缓解） |
| LLM Adapter | 直接调用云端 API | 受限于网络延迟和 LLM 厂商速率限制 |
| 存储 | SQLite + LanceDB 本地文件 | 不支持远程访问，不跨进程共享 |

**V1 适用场景：** 单个开发者在本地使用 CLI 辅助编码。一个项目同时只能有一个活跃的 CLI Session（多终端可以开，但并发写 LTM 需要重试）。

#### 6.8.2 V2 — Web API + 远程存储

```
┌─────────────────────────────────────────────────────┐
│  云端 (AWS / GCP / Azure)                            │
│  ┌───────────┐    ┌────────────┐                    │
│  │ web-api   │◄──►│ PostgreSQL │                    │
│  │ (容器/    │    │ (LTM +     │                    │
│  │  serverless)│   │  AgentMem) │                    │
│  └───────────┘    └────────────┘                    │
│       │                ▲                              │
│  ┌────┴────┐          │                              │
│  │ Redis   │◄─────────┘ (会话管理 + 分布式锁)         │
│  └─────────┘                                        │
│  ┌───────────┐                                      │
│  │ LanceDB/  │ V1 本地 → V2 迁移到 Pinecone/Milvus   │
│  │ Pinecone  │ (支持远程并发访问)                     │
│  └───────────┘                                      │
└─────────────────────────────────────────────────────┘
         ▲                    ▲
    CLI 用户              Web API 前端
```

| 变化 | V1 | V2 |
|------|-----|-----|
| **入口** | CLI only | + REST/WS API (支持 Web/Dashboard) |
| **存储后端** | SQLite 本地文件 | PostgreSQL RDS + Redis Cluster |
| **并发能力** | 单机单用户（WAL 缓解部分冲突） | 多用户并发，分布式锁保证 Session 安全 |
| **向量检索** | LanceDB 本地文件 | Pinecone/Milvus (远程服务) |

#### 6.8.3 V3 — 生产级部署

```
┌──────────────────────────────────────────────────────┐
│  K8s Cluster                                         │
│  ┌─────────┐  ┌─────────┐                           │
│  │ web-api │  │ web-api │  Auto Scaling (HPA)        │
│  │ Pod ×N  │  │ Pod ×N  │                            │
│  └────┬────┘  └────┬────┘                            │
│       │            │                                  │
│  ┌────┴────────────┴────┐                             │
│  │  PostgreSQL (Primary + Replica)                    │
│  │  Redis Cluster (3 nodes)                           │
│  │  Pinecone / Milvus (向量检索)                       │
│  └───────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────┤
│  Prometheus + Grafana (可观测性)                       │
│  OpenTelemetry Collector (链路追踪)                    │
└──────────────────────────────────────────────────────┘
```

| 变化 | V2 | V3 |
|------|-----|-----|
| **编排** | 容器/Serverless | K8s + HPA 自动扩缩容 |
| **多租户** | — | RBAC + tenant_id 列隔离 |
| **安全** | TLS | + mTLS + API Gateway + Rate Limiting |
| **可观测性** | Console Logger | Prometheus Metrics + Grafana Dashboard + Alerting |

#### 6.8.4 CLI vs Web API 的架构差异

```
┌─────────────────┬───────────────────────┬──────────────────────┐
│                 │ CLI (V1)              │ Web API (V2+)        │
├─────────────────┼───────────────────────┼──────────────────────┤
│ 运行时          │ Node.js (本地进程)     │ 容器/Serverless       │
│ Session 生命周期│ 进程内 Map + SQLite    │ Redis + PostgreSQL   │
│ 并发控制        │ SQLite WAL + 重试      │ Redis 分布式锁       │
│ Agent Memory    │ ~/.agent-platform/     │ PostgreSQL (tenant_id)│
│ LLM 调用延迟    │ ~200-500ms (直连)      │ ~300-800ms (加网络跳数)│
│ 部署复杂度      │ npm install -g         │ Docker + Cloud       │
└─────────────────┴───────────────────────┴──────────────────────┘
```

---

### 6.9 速率限制与 Token 配额管理 (Rate Limiting & Quota)

#### 6.9.1 CLI 层速率限制

V1 CLI 是本地工具，速率限制主要保护用户免受 LLM 厂商的速率惩罚：

```typescript
/** per-instance 令牌桶，V2 Web API 多实例部署需迁移到 Redis */
class RateLimiter {
  // 每模型独立的令牌桶算法
  private buckets = new Map<string, TokenBucket>();

  /** 获取或创建指定模型的令牌桶 */
  private getBucket(model: string): TokenBucket {
    if (!this.buckets.has(model)) {
      this.buckets.set(model, new TokenBucket({
        rate: this.getRateForModel(model),   // 从模型配置读取（如 Claude: 4 req/s, 80k tokens/min）
        burst: this.getBurstForModel(model),  // 突发容量 = 2x rate
      }));
    }
    return this.buckets.get(model)!;
  }

  /** 等待令牌可用后执行 */
  async withThrottle<T>(model: string, fn: () => Promise<T>): Promise<T> {
    const bucket = this.getBucket(model);
    await bucket.acquire();   // 阻塞直到有可用令牌
    return fn();
  }

  private getRateForModel(model: string): number {
    // 默认保守值，用户可通过 PlatformConfig.overrides 覆盖
    const defaults: Record<string, { rate: number; burst: number }> = {
      'claude': { rate: 4, burst: 8 },       // 4 req/s
      'gpt-4':   { rate: 3, burst: 6 },       // 3 req/s
    };
    return defaults[model]?.rate ?? 5;
  }

  private getBurstForModel(model: string): number {
    const defaults: Record<string, { rate: number; burst: number }> = {
      'claude': { rate: 4, burst: 8 },
      'gpt-4':   { rate: 3, burst: 6 },
    };
    return defaults[model]?.burst ?? 10;
  }
}

class TokenBucket {
  private tokens: number;
  private readonly rate: number;     // 每秒补充令牌数（必须 > 0）
  private readonly capacity: number; // 桶容量（突发上限）
  private lastRefill = Date.now();

  constructor({ rate, burst }: { rate: number; burst: number }) {
    if (rate <= 0) throw new Error(`TokenBucket rate must be > 0, got ${rate}`);  // 防止除零/死循环
    this.rate = rate;
    this.capacity = burst;
    this.tokens = burst;
  }

  async acquire(): Promise<void> {
    while (true) {
      this.refill();   // 按时间补充令牌
      if (this.tokens >= 1) {
        this.tokens -= 1;
        return;
      }
      // 等待下一个令牌可用（最多等 500ms，防止 rate 极小时无限等待）
      const waitMs = ((1 - this.tokens) / this.rate) * 1000;
      await sleep(Math.min(waitMs, 500));
    }
  }

  private refill() {
    const elapsed = (Date.now() - this.lastRefill) / 1000;
    this.tokens = Math.min(this.capacity, this.tokens + elapsed * this.rate);
    this.lastRefill = Date.now();
  }
}
```

#### 6.9.2 Token 配额管理（防超额消费）

| 层级 | 机制 | 说明 |
|------|------|------|
| **Agent Loop** | `calculateTokenBudget()` | 每个 Agent 迭代累计 token，超过阈值时 compact STM |
| **Session 级配额** | `session.quota.maxTokens` | 用户可配置单 Session 最大 token 用量（默认无限制） |
| **全局日配额** | `PlatformConfig.dailyTokenLimit` | 可选：每日总 token 上限，超限时拒绝新请求并通知用户 |

```typescript
/** QuotaManager — 完整 PlatformConfig 定义见 6.10。此处仅展示配额相关字段的使用示例。*/

/** CLI 层配额跟踪（SQLite 持久化，跨重启不丢失） */
class QuotaManager {
  constructor(
    private db: { query: (sql: string, params: unknown[]) => Promise<number> },
    private config: Pick<PlatformConfig, 'rateLimiting'>,
  ) {}

  async consumeTokens(sessionId: string, usage: TokenUsage): Promise<void> {
    const dailyUsed = await this.getDailyUsage();
    
    if (this.config.rateLimiting?.dailyTokenLimit && dailyUsed + usage.totalTokens > this.config.rateLimiting.dailyTokenLimit) {
      throw new QuotaExceededError(`Daily token limit reached. Used ${dailyUsed}/${this.config.rateLimiting.dailyTokenLimit}`);
    }

    // 记录到 SQLite（使用参数化查询防 SQL 注入）
    await this.db.query(
      'INSERT INTO token_usage (session_id, prompt_tokens, completion_tokens, total_tokens, timestamp) VALUES (?, ?, ?, ?, ?)',
      [sessionId, usage.promptTokens, usage.completionTokens, usage.totalTokens, Date.now()],
    );
  }

  async getDailyUsage(): Promise<number> {
    const row = await this.db.query(
      'SELECT COALESCE(SUM(total_tokens), 0) as total FROM token_usage WHERE date(timestamp / 1000, \'unixepoch\') = date(\'now\')',
      [],
    );
    return (row as { total: number })?.total ?? 0;
  }
}
```

---

### 6.10 配置管理 (PlatformConfig)

#### 6.10.1 全局配置结构

`PlatformConfig` 是平台启动时读取的唯一配置入口，所有组件通过 `PluginContext.config` 访问只读副本：

```typescript
interface PlatformConfig {
  /** ── LLM 配置 ── */
  llm: {
    defaultModel: string;                  // 默认模型（如 "claude-sonnet-4-20250514"）
    fallbackModels?: string[];             // 降级模型列表
    apiKey: string;                        // V1: 单 Key（开发用途）。生产环境必须通过环境变量 AGENT_PLATFORM_API_KEY 覆盖，或使用系统密钥环（keychain/keystore）。V2+: 支持多 Key 轮换。
    baseUrl?: string;                      // 自定义 API Endpoint（代理/本地模型）
    timeoutMs?: number;                    // 默认超时（ms），覆盖厂商默认值
    maxRetries?: number;                   // 非熔断类重试次数
  };

  /** ── 存储配置 ── */
  storage: {
    sqlitePath: string;                    // V1: SQLite 文件路径（默认 ~/.agent-platform/platform.db）
    ltmDbPath: string;                     // LTM KV 存储路径
    vectorStorePath: string;               // LanceDB 索引路径
  };

  /** ── Plugin/Skill 来源 ── */
  extensions: {
    pluginDirs: string[];                  // 本地插件目录列表
    registryUrl?: string;                  // 插件注册中心 URL（V2+）
    allowedSources: ('directory' | 'registry' | 'git')[];  // 允许的来源类型
  };

  /** ── 安全配置 ── */
  security: {
    commandWhitelist?: string[];           // 允许执行的命令列表（默认：cat, grep, ls, echo...）
    commandBlacklist?: string[];           // 禁止的命令模式（默认：rm -rf, drop, exec）
    allowedPaths: string[];                // 允许访问的文件路径前缀
    secretDetectionEnabled?: boolean;      // 是否启用 Secret 扫描（默认 true）
  };

  /** ── Agent 委派配置 ── */
  delegation?: { maxDepth?: number };     // L2：嵌套委派深度上限（default: 5）

  /** ── 速率限制 ── */
  rateLimiting: {
    requestsPerSecond?: number;            // 全局 QPS 限制（默认 5）
    dailyTokenLimit?: number;              // 每日 Token 上限（0 = 无限制）
  };

  /** ── 可观测性 ── */
  observability: {
    logLevel: 'debug' | 'info' | 'warn' | 'error';  // 默认 "info"
    structuredLogs?: boolean;             // V2+: 是否输出 JSON 日志
    otelEndpoint?: string;                // OpenTelemetry Collector endpoint（V3+）
  };

  /** ── Agent 覆盖配置 ── */
  agentOverrides: Record<string, Partial<Agent>>;  // 用户可覆盖特定 Agent 的配置（模型、参数等）
}
```

#### 6.10.2 配置加载优先级

```
命令行参数 (--model=gpt-4)    ← 最高优先级，仅影响当前进程
环境变量 (AGENT_PLATFORM_MODEL)
用户配置文件 (~/.agent-platform/config.json)
内置默认值 (PlatformConfig defaults)   ← 最低优先级
```

#### 6.10.3 配置验证

平台启动时执行配置校验，无效配置直接退出而非静默使用默认值：

```typescript
function validateConfig(config: PlatformConfig): ConfigValidationError[] {
  const errors: ConfigValidationError[] = [];
  
  if (!config.llm.apiKey || config.llm.apiKey.length < 10) {
    errors.push({ field: 'llm.apiKey', message: 'API Key 不能为空且长度需 >= 10' });
  }
  
  if (config.storage.sqlitePath && !isAbsolute(config.storage.sqlitePath)) {
    errors.push({ field: 'storage.sqlitePath', message: '必须是绝对路径' });
  }
  
  // ...更多校验
  
  return errors;
}
```

---

### 6.11 版本兼容性策略 (Version Compatibility)

#### 6.11.1 Agent/Plugin/Skill Semver 升级影响

| 组件 | Major 变更影响 | Minor 变更影响 | Patch 变更影响 |
|------|---------------|---------------|---------------|
| **Agent** | 新 Agent 定义，旧 Session 不兼容（记忆格式可能变化） | 新增工具/技能，旧 Session 可继续使用 | systemPrompt 微调，不影响已有行为 |
| **Plugin** | Handler 接口变更，热重载时活跃会话必须切换或结束 | 新增 Hook/工具，向后兼容 | Bug 修复，热重载即时生效 |
| **Skill** | 模板语法大改，旧 Session 渲染可能失败 | 新增变量/示例，向后兼容 | 文案微调，无行为影响 |

#### 6.11.2 平台版本升级时的处理策略

```typescript
interface PlatformVersion {
  major: number;    // 破坏性变更时递增
  minor: number;    // 向后兼容的新功能时递增
  patch: number;    // Bug 修复时递增
  
  /** 最低兼容的 Session 格式版本 */
  minSessionFormatVersion: number;
}

class Platform {
  private version: PlatformVersion = { major: 4, minor: 0, patch: 0, minSessionFormatVersion: 1 };
  private sessionStore: SessionStore;

  constructor(sessionStore: SessionStore) { this.sessionStore = sessionStore; }

  /** 启动时检查旧 Session 是否兼容 */
  async validateSessionCompatibility(): Promise<CompatibilityReport> {
    // 分页遍历所有历史 Session，避免 OOM
    const incompatible: string[] = [];
    let page = 0;
    while (true) {
      const sessions = await this.sessionStore.listAll(page, 100);
      if (sessions.length === 0) break; // 无更多数据，结束遍历
      
      for (const session of sessions) {
        if (session.formatVersion < this.version.minSessionFormatVersion) {
          incompatible.push(session.id);
          // V1 策略：标记为不可恢复，建议用户创建新 Session
          await this.sessionStore.markDeprecated(session.id, {
            reason: `Session format v${session.formatVersion} is deprecated in platform v${this.version.major}.${this.version.minor}`,
            migratedAt: Date.now(),
          });
        }
      }
      
      if (sessions.length < 100) break; // 最后一页，结束遍历
      page++;
    }
    
    return { total: incompatible.length + (page * 100), incompatible };
  }

  /** Session 格式版本迁移（仅在 Major 变更时需要） */
  async migrateSessionFormat(sessionId: string, fromVersion: number): Promise<void> {
    // V1→V2：AgentMemory 从扁平 Record 改为结构化知识/经验/偏好三字段
    if (fromVersion === 1 && this.version.minSessionFormatVersion >= 2) {
      const raw = await this.loadRawSession(sessionId);
      await this.saveMigratedSession(sessionId, {
        ...raw,
        formatVersion: 2,
        // 自动迁移：将旧格式数据拆分到新结构
        agentMemory: this.migrateAgentMemoryV1ToV2(raw.agentMemory),
      });
    }
  }

  /** 用于 Session 迁移的私有方法 */
  private async loadRawSession(sessionId: string): Promise<Record<string, unknown>> { /* ... */ return {}; }
  private async saveMigratedSession(sessionId: string, data: Record<string, unknown>): Promise<void> { /* ... */ }
  private migrateAgentMemoryV1ToV2(raw: Record<string, unknown> | undefined): AgentMemory['knowledge'] { /* ... */ return {}; }
}
```

#### 6.11.3 V1 兼容性保证

- **向后兼容**：Minor/Patch 升级不会破坏已有 Session 的恢复能力
- **Migration Hook**：Agent Memory 格式变更时，通过 `onRestore()` 传递迁移快照
- **Graceful Degradation**：旧 Plugin 在新平台上运行时，如果缺少新接口（如 `getHooks`），静默跳过而非报错

---

## 七、Session Lifecycle

### 7.1 Session 生命周期状态机

```
                    ┌─────────────┐
                    │   Created    │ ← Platform.createSession()
                    └──────┬──────┘
                           │
                           ▼
              session:start Hook (priority-ordered)
                           │
                           ▼
           ┌──────────────────────────────┐
           │        Active                │ ◄── 用户交互 / Agent Loop
           └──────┬───────────────────────┘
                  │ error / unrecoverable failure
                  ▼
           ┌─────────────┐
           │   Failed    │ ← Session 异常终止，保留状态供调试
           └──────┬──────┘
                  ├─ recover? → session:start（允许从失败中恢复）
                  │ session:end Hook (clear all session hooks)
                  ▼
                    ┌─────────────┐
                    │   Ended     │ ← Session 数据持久化到 LTM/Vector
                    └─────────────┘
```

**状态说明：** `Failed` 是新增的错误态。当 Agent Loop 遇到不可恢复错误（LLM 持续失败、权限被拒绝等）时进入此状态，Session Manager 执行清理并触发 `session:end` Hook，最终持久化数据到 `Ended`。这避免了直接崩溃或丢失会话上下文。

**Failed 态恢复机制：** Session Manager 提供 `recover(sessionId)` 方法，从 Failed 态重建 Session（重新创建 STM、激活 Skills、触发 session:start Hook）。适用于 P1 Critical 错误中的可恢复场景。对于不可恢复错误（数据损坏），直接走 Ended。

`recover()` 触发的 `session:start` Hook 与新建 Session 时完全相同，确保插件和 Skill 能正确初始化。

### 7.2 Session Manager — 会话管理核心

```typescript
interface Session {
  id: string;
  status: 'created' | 'active' | 'failed' | 'ended';
  agentId: string;                   // Agent ID (Agent 是一等公民)
  projectRoot: string;

  // 关联的子系统实例（每个 Session 独立）
  stm: ShortTermMemory;              // 会话级对话历史

  // Plugin 状态隔离：每个 Session 有自己的 Hook 注册和 Skill 激活集
  activeSkillIds: string[];          // 当前激活的 Skill ID 列表

  /** Session 级 Token 配额（防超额消费） */

  quota?: { maxTokens?: number };    // 用户可配置单 Session 最大 token 用量（默认无限制）

  /** 存储层字段 — Session format version，用于 Major 版本升级时的迁移校验。此字段仅由 Platform 的兼容性检查方法使用。 */
  formatVersion?: number;

  /** 存储层兼容字段 — Agent Memory 本属 Agent 级，旧格式将其嵌套在 Session 中。
   * 新代码应通过 AgentMemoryStore 存取，此字段仅用于 Major 版本迁移时的临时读取和拆分。 */
  agentMemory?: Record<string, unknown>;
}

/**
 * SessionManager 完整实现见 6.7（并发与多用户支持）。
 * 此处仅列出接口摘要，避免代码重复。
 *
 * H4 修正：6.7 是权威实现（含 recover、listByProject），本章不重复定义。
 */
// class SessionManager { ... } — 参见 6.7
```

### 7.3 补充类型声明

以下类型在文档各处以引用但未声明，在此集中补齐：

```typescript
/** SessionManager.create() 的参数类型 */
interface CreateSessionOptions {
  sessionId?: string;          // 可选，未提供时自动生成
  agentId: string;             // 目标 Agent ID
  projectRoot: string;         // 项目根目录
}

/** Platform.validateSessionCompatibility() 返回值 */
interface CompatibilityReport {
  total: number;               // Session 总数
  incompatible: string[];      // 不兼容的 Session ID 列表
}

/** 配置验证错误 */
interface ConfigValidationError {
  field: string;               // 字段路径，如 "llm.apiKey"
  message: string;             // 人类可读的错误说明
}

/** HookBus.listHooks() 返回的已注册 Hook 信息 */
interface RegisteredHook {
  event: HookEvent;            // 监听的事件类型
  pluginId: string;            // 注册插件 ID
  priority: number;            // 优先级
  once?: boolean;              // 是否只触发一次
}

/** PluginManifest.dependsOn 的版本范围类型 */
type VersionRange = string;    // Semver 范围字符串，如 ">=1.0.0 <2.0.0"

/** Session 存储层接口 — 用于 Platform 的 Session 持久化操作 */
interface SessionStore {
  /** V2+ 必须分页，V1 CLI 默认 page=0, pageSize=100 */
  listAll(page?: number, pageSize?: number): Promise<(Session & { formatVersion?: number; agentMemory?: Record<string, unknown> })[]>;
  get(id: string): Promise<(Session & { formatVersion?: number }) | undefined>;
  save(session: Session & { formatVersion?: number }): Promise<void>;
  markDeprecated(id: string, info: { reason: string; migratedAt: number }): Promise<void>;
}

/** 自定义错误类 */
class SecurityError extends Error { readonly name = 'SecurityError'; constructor(msg: string) { super(msg); } }
class CircuitOpenError extends Error  { readonly name = 'CircuitOpenError';  constructor(msg: string) { super(msg); } }
class QuotaExceededError extends Error{ readonly name = 'QuotaExceededError'; constructor(msg: string) { super(msg); } }

/** TokenBucket — 见 6.9.1 完整实现 */
// class TokenBucket { ... }  ← 请参见 6.9.1 的完整实现

/** Helper Functions */
// sleep(ms)              — 通用延迟工具函数（返回 Promise）
// formatError(err: Error): string — 将 Error 对象格式化为人类可读字符串
// scanForPatterns(text: string, patterns: RegExp[]): Match[] — 正则模式扫描，返回匹配项列表

### 7.4 Agent vs Session 记忆关系 (v4 新增)

| 资源 | 隔离级别 | 说明 |
|------|----------|------|
| **Hook 注册** | 会话级 (`onSession`) | 每个 Session 有独立的 Hook 执行上下文 |
| **Plugin 实例** | 全局单例 | PluginManager 只维护一个 Plugin 实例（除非热重载） |
| **Agent 实例** | 全局注册，每次委派创建新 Session | AgentRegistry 管理 Agent 定义；每次 `delegate_to_agent` 创建新的 Session |
| **STM (短期记忆)** | 会话级隔离 | 每个 Session 独立的 Ring Buffer，自动压缩（`compact()`）释放 token 预算 |
| **Agent Memory** | Agent 级持久化 | 跨会话共享（V1 单用户）。Coding Agent 从上次任务中学到的经验，下次继续用。存储路径：`~/.agent-platform/agents/{agentId}/memory.json` |
| **Project LTM (长期记忆)** | 项目级共享 | KV + SQLite/Postgres，显式保存学到的知识（技术栈、决策、偏好）。多 Session 读同一份 |
| **Vector Store** | 项目级语义检索 | Embedding 向量，支持模糊匹配和代码检索。V1：LanceDB 本地文件；V2+：Pinecone/Milvus |
| **Hook Bus** | 全局事件总线 | 所有 Session 共享，`onSession()` 可注册会话级 Hook（自动在 `clearSession()` 时清理） |

---

## 八、Monorepo 包结构 (v4 重构)

```
agent-platform/
├── packages/
│   ├── shared-types/          # 零依赖接口定义
│   │   ├── chat.ts            # ChatMessage, ToolCall, ChatResponse...
│   │   ├── agent.ts           # Agent, AgentMemory, AgentRegistry (v4 新增)
│   │   ├── hook.ts            # HookEvent, HookContext, HookRegistration
│   │   ├── plugin.ts          # PluginManifest, Permission...
│   │   └── skill.ts           # SkillManifest, SkillBundle...
│   │
│   ├── hook-core/             # HookBus 实现（从 plugin-core 下沉）
│   │   ├── HookBus.ts         # HookBus 类 — 优先级队列 + 错误隔离 + 深度限制
│   │   └── index.ts
│   │
│   ├── plugin-core/           # Plugin 生命周期管理（依赖 hook-core + shared-types）
│   │   ├── PluginManager.ts   # 发现、加载、依赖解析、热重载
│   │   └── index.ts
│   │
│   ├── skill-core/            # Skill 发现和渲染
│   │   ├── SkillRegistry.ts   # 加载、发现、激活、模板渲染
│   │   ├── template-engine.ts  # Handlebars {{variable}} 渲染器
│   │   └── index.ts
│   │
│   ├── llm-adapter/           # LLM 抽象层 (Anthropic/OpenAI/Google/自定义)
│   ├── tool-core/             # ToolRegistry — 依赖 hook-core, shared-types
│   │
│   ├── tools/                 # 标准工具处理器 (每个独立包，实现 ToolHandler)
│   │   ├── filesystem/        # 文件读写编辑搜索
│   │   ├── git/               # Git 操作
│   │   ├── terminal/          # Shell 执行
│   │   └── web/               # 网页搜索/抓取 (V2)
│   │
│   ├── memory-stm/            # 短期记忆 (Ring Buffer + 压缩) — 依赖 hook-core, shared-types
│   ├── memory-ltm/            # 长期记忆 (KV + SQLite/Postgres) — 依赖 hook-core, shared-types
│   │                              # memory-vector/ 见 Phase 2（语义检索 V2 引入）
│   │
│   ├── orchestrator-agent/    # v4 新增：Orchestrator Agent 定义 + 委派工具
│   │   ├── src/orchestrator.ts  # Orchestrator Agent 实例定义
│   │   ├── src/delegate-tool.ts # delegate_to_agent ToolHandler
│   │   └── index.ts
│   │
│   ├── agents/                # v4 重构：Agent 注册中心 + 内置 Agent 集合
│   │   ├── src/agent-registry.ts # AgentRegistry (从 shared-types 中搬入)
│   │   ├── src/coding-agent.ts   # Coding Agent 定义
│   │   ├── src/review-agent.ts   # Review Agent 定义
│   │   └── index.ts            # 导出所有内置 Agent + AgentRegistry
│   │
│   ├── plugins/               # 官方平台插件
│   │   ├── tdd-plugin/        # TDD 工具 + Hook + Skill 引用
│   │   ├── security-plugin/   # 安全工具 + Hook (tool:beforeExecute 拦截)
│   │   └── logging-plugin/    # 内置可观测性 Hook
│   │
│   ├── skills/                # 官方平台技能包 (纯文本)
│   │   ├── tdd-workflow/      # TDD 系统提示模板
│   │   ├── owasp-security-review/
│   │   └── refactoring-patterns/
│   │
│   └── platform/              # 组合根工厂 (组装一切)
├── apps/
│   ├── cli/                   # CLI 入口
│   └── web-api/               # REST/WebSocket API (V2)
└── docs/adr/                  # 架构决策记录
```

### 包依赖关系图（修正版）

```
                    shared-types
                       │
            ┌──────────┼───────────────┐
            ▼          ▼               ▼
       hook-core   skill-core    llm-adapter
            │                     │     │
      tool-core                   │  memory-stm/ltm/vector  (memory 依赖 hook-core)
            │                     │
      tools/* (实现 ToolHandler，不引用 skill-core)
            │
   orchestrator-agent (依赖 llm-adapter, tool-core, shared-types)
            │
         agents ──► (agent-registry + 内置 Agent 定义)
            │
   platform (组装一切: hook-core, plugin-core, agent-registry, orchestrator-agent, ...)
            │
     apps/cli, apps/web-api

plugins/* ──► 依赖 tool-core + plugin-core + hook-core + shared-types
skills/    ──► 纯文本，无代码依赖
```

**关键修正：**
- `hook-core` 从 `plugin-core` 中独立出来，成为零依赖的核心基础设施包
- `tool-core` / `memory-*` 只依赖 `hook-core`（通过注入 HookBus 实例），不依赖 `plugin-core`
- `tools/*` 实现 `ToolHandler` 接口，不引用 `skill-core`
- **新增 orchestrator-agent/** — Orchestrator Agent 的定义和委派工具独立成包
- **重构 agents/** — 从纯配置改为 Agent 注册中心 + 内置 Agent 集合

---

## 九、V1 vs V2 vs V3 范围对比

| 组件 | V1 (编码智能体 MVP) | V2 (全能平台) | V3 (生产级多租户) |
|------|---------------------|---------------|-------------------|
| **Agent** | Orchestrator Agent + Coding Agent | + Review/Test/Research Agents | + 用户自定义 Agent 模板 |
| **工具处理器** | filesystem, git, terminal | + web, docker, database | + 第三方插件市场 |
| **LLM Adapter** | Anthropic Claude (V1 够用) | + OpenAI, Google, 本地模型 | + 自动路由(成本/延迟最优) |
| **Plugin System** | hook-core + plugin-core 框架 | + TDD/Security 官方 Plugin | + 第三方插件审核机制 |
| **Skill System** | hook-core + skill-core 框架 | + TDD/Security/Refactoring Skills | + 用户自定义 Skill 市场 |
| **记忆存储** | SQLite (LTM) + LanceDB (Vector, 本地文件) | PostgreSQL + Redis Cluster | + 分布式缓存 |
| **入口** | CLI (终端) | + Web API (REST/WS) | + IDE Extension + Slack/Discord Bot |
| **并发控制** | SQLite WAL + Session 写重试 | Redis 分布式锁 | K8s Pod 级隔离 |
| **多用户** | 单用户本地使用（OS 目录隔离） | — | RBAC + tenant_id 列隔离 |
| **部署** | npm install -g (无需服务器) | Docker/Serverless + RDS | K8s Cluster + Auto Scaling |
| **安全沙箱** | Hook 拦截 + 命令白名单 | + 容器隔离 | + RBAC + 多租户隔离 |
| **可观测性** | Console Logger | + Structured Logging + Tracing | + Metrics Dashboard + Alerting |
| **速率限制** | Token Bucket (CLI 层) | API Gateway Rate Limiting | 分布式配额管理 |
| **配置管理** | config.json + 环境变量 | + YAML 多环境配置 | + ConfigMap/K8s Secret |
| **版本兼容** | Session format v1，无迁移 | format migration hook | Major 升级自动迁移旧 Session |

---

## 十、演进路径

```
Phase 1: 核心基础设施 (编码智能体 MVP)
  ├── shared-types, hook-core, plugin-core
  ├── llm-adapter(Anthropic), tool-core
  ├── tools/filesystem, git, terminal
  ├── memory-stm(lru), memory-ltm(sqlite)
  ├── orchestrator-agent (Orchestrator Agent + delegate_to_agent)
  ├── agents (内置 Coding Agent, Review Agent)
  └── apps/cli

Phase 2: 扩展生态 (全能平台)
  ├── skill-core (Skill Registry + Template Engine)
  ├── llm-adapter 添加 OpenAI/Google adapter
  ├── tools/web, docker
  ├── plugins/tdd-plugin, security-plugin
  ├── skills/tdd-workflow, owasp-security-review
  ├── memory-vector (语义检索)
  └── apps/web-api

Phase 3: 生产级 (多租户/企业级)
  ├── memory-ltm 迁移 PostgreSQL + Redis Cluster
  ├── 安全沙箱(容器隔离) + RBAC
  ├── Metrics Dashboard + Distributed Tracing
  ├── IDE Extension + Slack/Discord Bot
  └── 第三方插件市场 + 审核机制
```

---

## 十一、关键设计决策记录 (ADR)

### ADR-001: 为什么不用 MCP?

**当前理由：** MCP 的传输层(HTTP/SSE/WebSocket)对单应用 Agent 来说是多余的复杂度。我们的 `ToolHandler` 协议捕获了 80% 的价值（工具即插即用），但只有 20% 的复杂度。如果需要跨进程工具服务器，可以在上面包一层 Adapter。

**补充说明 (V2 再看)：** MCP 在 2024-2025 年已发展出 cross-process tool server、model-agnostic protocol 等特性。如果 V2 Web API 阶段需要跨语言/跨进程工具服务（如独立 LSP 作为工具服务器），可以重新评估 MCP。**决策：V1 不用，V2 Web API 阶段重新评估 MCP 适配性（跨工具共享插件需求）。**

### ADR-002: Agent 是一等公民 (v4 核心决策)

**Agent 不是配置对象，是有身份、能力边界、工具集、记忆、技能的独立实体。** Orchestrator 本身也是一个 Agent。

**对比 LangGraph/AutoGen：**
- LangGraph：支持状态机驱动（节点是函数），但也支持自然语言流模式。添加新节点需要改代码，但可通过动态图构建缓解。**我们的区别**：Agent 不是图节点，而是独立实体；通过工具调用协作而非共享状态图，用户无需定义完整的有向图结构
- AutoGen：Agent 通过对话通信，无限循环问题有 `max_turns` / `is_termination_msg` 等解决方案，但默认配置下仍容易陷入。**我们的区别**：强制通过 Orchestrator 路由（而非 Agent 直连对话），配合 MAX_DELEGATION_DEPTH 从架构层面杜绝递归

**对比 Claude Code：**
- Claude Code 是单 Agent（线性对话），没有多 Agent 概念
- 我们支持用户自定义多个专业 Agent，由 Orchestrator 编排

### ADR-003: Orchestrator 本身就是一个 Agent (v4)

Orchestrator 不是独立的管理器类。它是一个特殊的 Agent：
- **身份**："编排者"
- **人格**：系统提示词告诉它"你是指挥官，不是执行者"
- **工具集**：`delegate_to_agent` + 辅助工具（日志、文件读取）
- **记忆**：有自己的 STM（记录委派历史）

**为什么不用单独的 Orchestrator 类？**
1. **统一抽象**：所有 Agent 共享同一个 Universal Loop，减少代码重复
2. **可扩展性**：用户可以定义自己的"编排者变体"（如专注测试编排的 Orchestrator）
3. **可替换**：需要不同编排策略时，只需换一个 Orchestrator Agent 配置

### ADR-004: 为什么记忆分三层?

STM(对话)需要快速追加和滑动窗口；LTM(知识)需要精确的 KV 查找和分类检索；Vector(语义)需要模糊匹配。三种访问模式对应三种存储方案，混在一起只会增加复杂度。

### ADR-005: 为什么用 Monorepo?

包之间的接口变更需要同步更新和测试。Monorepo (pnpm workspace + Turborepo)保证所有依赖包的类型安全和测试在同一个 CI 流程中完成。每个工具处理器也可以独立发布。

### ADR-006: Plugin System — 统一的能力扩展机制

一个 Plugin Package 可同时提供工具、Skill 引用和 Hook 注册，通过声明式 Manifest 管理依赖。比纯工具系统更通用，比完整框架更轻量。

**对比 LangChain Chains/LCEL：** LCEL 是 DSL 式的链式调用，需要学习新语法且耦合在 LangChain 生态内。我们的 Plugin 系统是原生的 TypeScript 模块，无 vendor lock-in，能力维度更广（工具 + Skill + Hook）。

### ADR-007: Skill 是文本包不是可执行代码

Skill 通过渲染模板注入系统提示词来引导 Agent，不执行任何代码。**安全**（无需沙箱）、**可读**（diff-friendly YAML+Markdown）、**低门槛**（非程序员也能写）。复杂逻辑交给 Plugin 的 Hook。

### ADR-008: Hook Bus — 优先级队列 + 错误隔离 + 深度限制

每个 Handler 包裹在 try/catch 中，单个失败不影响链。**优先级**保证执行顺序可预测（核心→插件→用户）。`shortCircuit` 让关键 Hook（如安全检查）能阻断流程。**深度限制**防止 memory:beforeWrite 等可修改数据的 Hook 导致无限循环。

### ADR-009: 安全纵深防御 — 五层模型

单一安全措施不可靠（白名单会被绕过、沙箱可能有漏洞）。五层防御确保即使一层失效，其他层仍然提供保护。**权限上下文 + Hook 拦截 + 命令过滤 + 文件隔离 + 审计日志** 覆盖攻击面。

### ADR-010: 错误处理 — Circuit Breaker + Fallback Chain

LLM API 不是 100% 可靠的。Circuit Breaker 防止雪崩（连续失败后快速返回，不浪费请求），Fallback Chain 提供降级路径（主模型不可用时用备用模型）。两者结合确保平台韧性。

### ADR-011: 测试 — Contract Testing for LLM Adapter

LLM Adapter 有 N 个实现（Anthropic/OpenAI/Google...），每个必须遵守相同的契约。共享测试套件确保新增 adapter 时不会破坏已有行为。**这是多 Provider 架构的必选项，不是可选项。**

### ADR-012: Hook Bus 独立为 hook-core 包 (修正 v3 的依赖扩散问题)

v3 设计中 HookBus 放在 plugin-core 中导致 tool-core / memory-* 全部依赖 plugin-core。这违反了"核心基础设施不应依赖生命周期管理模块"的原则。

**修正：** 将 HookBus 实现下沉到独立的 `hook-core` 包，只包含事件路由逻辑（无 Plugin 概念）。`plugin-core` 依赖 `hook-core` 来提供 Plugin 的 Hook 注册能力。tool-core / memory-* 通过注入 HookBus 实例使用 Hook，只依赖 hook-core 的类型声明。

### ADR-013: ToolHandler 重命名 (修正 v3 的命名冲突)

v3 中 `ToolPlugin`（工具处理器窄接口）和 `Plugin`（扩展宽接口）同名但语义完全不同，造成混淆。

**修正：** `ToolPlugin` → `ToolHandler`。ToolHandler 是单个工具的声明+执行；Plugin 是一个 Package 的整体能力声明（可包含多个 ToolHandler）。命名不再冲突。

### ADR-014: Plugin Hot-Reload — 活跃会话继续使用旧版 Hook

热重载时，活跃会话的 Hook 不能突然消失或切换到新版本（可能导致未完成的 Task 行为不一致）。

**策略：** 
- `hotReload(id)` 先暂停该 Plugin 的新 Hook 注册
- 活跃会话继续使用旧版 Handler（直到会话结束或用户手动切换）
- 新创建的会话使用新版
- 通过 `onUnload() → onRestore()` 传递状态快照，支持可选的状态迁移

### ADR-015: 工具并行执行 — 文件级锁

LLM 可能在一次响应中调用多个涉及同一文件的写操作（如同时 write_file: a.ts 和 edit_file: a.ts）。`Promise.all` 并行执行会导致竞态条件。

**策略：** 按 `{文件路径}:{读/写标记}` 分组——同文件写操作严格串行，同文件读操作可并行（多读安全），不同文件组完全并行。见架构总览 2.6 节 `executeToolCallsWithFileLock()` 实现。

### ADR-016: Token 预算追踪 — Agent Loop 内置

Agent Loop 不追踪 token 用量可能导致上下文溢出和意外费用。

**策略：** Orchestrator 在每个 Loop 迭代中累计 `response.usage.totalTokens`，超过 `TOKEN_BUDGET_PER_TASK` 时调用 `stm.compact()` 压缩旧消息释放空间。阈值可根据模型上下文窗口动态计算（如设置为 maxTokens 的 80%）。

### ADR-017: Plugin Discovery — 安全声明 + 分级验证

支持三种安装来源（目录/Registry/Git），每种有不同的安全风险。

**策略：** 
- Manifest 中必须声明 `permissions`（需要的权限列表）
- Registry 安装的插件需要签名验证
- Git URL 安装时显示权限声明清单供用户确认
- V3 阶段增加第三方插件审核机制

### ADR-018: Agent Memory — Agent 级持久化记忆 (v4)

Agent 需要有跨会话的长期记忆，记录专业知识和经验。这与 Session LTM（项目共享）不同：Agent Memory 是 Agent 专属的。

**设计：**
- `AgentMemory` 包含知识(KV)、经验(成功/失败模式)、偏好
- **V1**：每个 Agent 有独立的内存空间，跨会话共享；CLI 本地运行时按 OS 用户目录隔离（~/.agent-platform/agents/{agentId}/），不同 OS 用户之间不互通
- **V3**：迁移到 PostgreSQL，加 tenant_id 列，应用层做租户隔离
- 持久化到磁盘（SQLite），重启后恢复
- **不做向量搜索**：Agent Memory 是精确 KV + 结构化经验记录，语义检索由 Vector Store 负责

### ADR-019: Orchestrator Agent 的模型选择 (v4)

Orchestrator 需要强推理能力来分解任务和路由 Agent。

**策略：**
- Orchestrator 使用最强模型（如 Opus），因为它的输出直接影响整个流程的质量
- 专业 Agent 可以使用性价比更高的模型（如 Sonnet），因为它们专注特定领域
- **权衡**：Orchestrator 的 LLM 调用成本更高，但错误路由的成本远高于此

### ADR-020: V1 并发控制 — SQLite WAL + Session 写重试

V1 CLI 是本地工具，但同一个用户可能同时开多个终端窗口操作同一个项目。SQLite 在单文件级别需要处理并发写冲突。

**策略：**
- **WAL (Write-Ahead Logging) 模式**：允许并发读和单个写入者共存，读写不阻塞
- **Session STM（内存 Ring Buffer）**：进程内天然隔离，无并发问题
- **LTM/Agent Memory 写入**：SQLite INSERT OR REPLACE + 重试逻辑（最多 3 次，指数退避 10ms → 50ms → 250ms）
- **多终端场景**：每个 CLI 进程有自己的 Session Manager（Map），但共享同一个 SQLite 文件。写 LTM 时加锁保证顺序

**为什么不用 Redis 做 V1？** V1 目标是"npm install -g 即用"，Redis 引入额外部署依赖不符合 MVP 目标。SQLite WAL + 重试足以覆盖单用户多终端场景。

### ADR-021: 部署架构 — CLI-first, Serverless-ready

V1 CLI 本地运行无需服务器，但 Web API 需要支持容器化/Serverless 部署。不同阶段的基础设施差异很大，文档必须明确边界。

**策略：**
- **V1 (CLI-only)**：`npm install -g` 本地运行，SQLite + LanceDB 文件存储，无服务器依赖
- **V2 (Web API)**：Docker/Serverless（AWS Lambda / Cloud Run），PostgreSQL RDS + Redis Cluster，向量检索迁移到 Pinecone/Milvus
- **V3 (Production)**：K8s Cluster + HPA Auto Scaling，多副本部署

**为什么 CLI 先于 Web API？** 
1. CLI MVP 不需要服务器基础设施，开发迭代更快
2. Agent Loop 是计算密集型（LLM 调用 + 文件操作），本地运行无网络延迟问题
3. V1 验证核心架构后，Web API 只需替换存储后端（SQLite → PostgreSQL）和加并发控制（Redis 分布式锁）

### ADR-022: 速率限制 — Token Bucket (CLI 层)

LLM API 有速率限制（如 Claude 4 req/s），超出会被拒绝。V1 CLI 需要在本地实现速率限制，避免用户一次性触发过多请求导致被封禁。

**策略：**
- 每个模型独立的令牌桶算法（Token Bucket）
- 默认保守值（Claude: 4 req/s, GPT-4: 3 req/s），用户可通过 config 覆盖
- V2 Web API 层迁移到 API Gateway Rate Limiting
- 多 Key 轮换可作为补充策略（V2+）

### ADR-023: 配置管理 — 单一入口 + 验证

平台启动时读取 `PlatformConfig`，所有组件通过只读副本访问。无效配置由调用方决定处理方式（抛出异常退出或回退默认值）。

**策略：**
- **加载优先级**：命令行 > 环境变量 > config.json > 内置默认值
- **启动校验**：API Key 非空、路径为绝对路径等基础检查；`validateConfig()` 返回错误数组，由 Platform 入口决定是否终止（L5：描述与实现统一）
- **Agent Override**：用户可通过 `agentOverrides` 覆盖特定 Agent 的模型/参数，无需修改代码

### ADR-024: 版本兼容性 — Session Format Version + Migration Hook

平台 Major 版本升级时可能破坏旧 Session 的数据格式。必须提供迁移机制或明确的降级策略。

**策略：**
- 每个 Session 携带 `formatVersion`，平台声明 `minSessionFormatVersion`
- Minor/Patch 升级保证向后兼容（已有 Session 可恢复）
- Major 升级时运行 migration hook，自动迁移旧格式；无法迁移的标记为 deprecated
- Plugin `onRestore()` 传递迁移快照，支持 Agent Memory 等组件的自定义迁移逻辑

### ADR-025: TokenBucket — rate > 0 强制校验 (C3)

> 注：ADR-025/026 为代码层修正记录（来自 CRITICAL/MEDIUM 级别评审），非传统架构决策，但值得归档以防回归。

`TokenBucket.acquire()` 在 rate ≤ 0 时会进入死循环（tokens 永远不会增加）。必须在校验阶段拦截。

**策略：**
- 构造函数中 `if (rate <= 0)` 直接抛错，阻止非法实例创建
- `acquire()` 内最大等待时间截断为 500ms，防止 rate 极小时无限阻塞

### ADR-026: LLMCallContext.tools 类型统一 (M7)

旧设计中 `tools: ToolHandler[]` 但 `modifiedTools: ToolDefinition[]`，Hook 修改后无法直接替换。改为两者同为 `ToolHandler[]`，调用方负责转换为 `ToolDefinition[]`。

**策略：**
- Hook 操作的是 `ToolHandler`（可执行对象），`llm.complete()` 接收的是 `ToolDefinition[]`（LLM 可见描述）
- 转换逻辑集中在调用处：`(modifiedTools ?? tools).map(t => t.getTools()).flat()`
