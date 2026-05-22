import { randomUUID } from 'node:crypto'
import type {
  Logger,
  PlatformConfig,
  Agent,
  AgentResult,
  ChatMessage,
  ToolCall,
  ToolHandler,
  ToolResult,
} from '@agent-platform/shared-types'
import { DEFAULT_CONFIG, consoleLogger } from '@agent-platform/shared-types'
import { ClaudeAdapter, OpenAIAdapter } from '@agent-platform/llm-adapter'
import type { LLMAdapter } from '@agent-platform/llm-adapter'
import { ToolRegistry, runAgentLoop } from '@agent-platform/tool-core'
import { ShortTermMemory } from '@agent-platform/memory-stm'
import { FilesystemHandler } from '@agent-platform/tools-filesystem'
import { GitHandler } from '@agent-platform/tools-git'
import { TerminalHandler } from '@agent-platform/tools-terminal'
import { DelegateToAgentHandler } from './tools/delegateTool.js'
import { buildAgent } from './agents.js'

export interface Session {
  id: string
  agentId: string
  projectRoot: string
  stm: ShortTermMemory
  messages: ChatMessage[]
}

export class Platform {
  private llm: LLMAdapter
  private registry: ToolRegistry
  private orchestratorAgent!: Agent
  private config: PlatformConfig
  private agentsCache = new Map<string, Agent>()
  private handlerMap = new Map<string, ToolHandler>()
  private sessions = new Map<string, Session>()
  private logger: Logger

  constructor(config: PlatformConfig, logger?: Logger) {
    this.config = { ...DEFAULT_CONFIG, ...config, llm: config.llm }
    this.logger = logger ?? consoleLogger

    const provider = this.config.llm.provider ?? 'anthropic'
    if (provider === 'openai') {
      this.llm = new OpenAIAdapter(this.config.llm, { logger: this.logger })
    } else {
      if (!this.config.llm.apiKey) {
        throw new Error('llm.apiKey required for anthropic provider (set ANTHROPIC_API_KEY env var or config file)')
      }
      this.llm = new ClaudeAdapter(this.config.llm, { logger: this.logger })
    }
    this.registry = new ToolRegistry(this.logger)

    const fsHandler = new FilesystemHandler(this.config.security?.allowedPaths, this.logger)
    const gitHandler = new GitHandler()
    const termWhitelist = this.config.security?.terminalWhitelist ?? undefined
    const termHandler = new TerminalHandler(termWhitelist, this.logger)

    for (const h of [fsHandler, gitHandler, termHandler]) {
      this.registry.register(h)
      this.handlerMap.set(h.id, h)
    }

    const delegateHandler = new DelegateToAgentHandler(
      { get: (id: string) => this.getAgent(id) },
      this.llm,
      this.registry,
      this.config.runtime?.compressionRatio,
      this.config.runtime?.maxToolRetries,
      config.agents,
    )
    this.registry.register(delegateHandler)
    this.handlerMap.set(delegateHandler.id, delegateHandler)

    // Build all agents from config.agents
    for (const agentConfig of config.agents) {
      const handlers = (agentConfig.tools ?? [])
        .map((id) => this.handlerMap.get(id))
        .filter(Boolean) as ToolHandler[]
      const agent = buildAgent(agentConfig, handlers, {
        contextWindow: this.config.runtime?.contextWindow,
      })
      this.agentsCache.set(agentConfig.id, agent)
      if (agentConfig.id === 'orchestrator') {
        const agentLines = config.agents
          .filter((a) => a.id !== 'orchestrator')
          .map((a) => `  - ${a.id}: ${a.description || a.name}`)
          .join('\n')
        agent.systemPrompt += `\n\n## 可用子 Agent\n\n${agentLines || '(无)'}`
        this.orchestratorAgent = agent
      }
    }

    if (!this.orchestratorAgent) {
      throw new Error('Platform requires an agent with id "orchestrator" in config.agents')
    }
  }

  private getAgent(id: string): Agent | undefined {
    return this.agentsCache.get(id)
  }

  createSession(agentId: string, projectRoot: string): Session {
    const session: Session = {
      id: randomUUID(),
      agentId,
      projectRoot,
      stm: new ShortTermMemory(undefined, this.config.runtime?.stmThreshold ?? 50),
      messages: [],
    }
    session.stm.resetCompactCount()
    return session
  }

  private getSessionKey(agentId: string, projectRoot: string): string {
    return `${agentId}::${projectRoot}`
  }

  async run(
    request: string,
    signal?: AbortSignal,
    onChunk?: (text: string) => void,
    onToolStart?: (call: ToolCall, agentId: string) => void,
    onToolFinish?: (call: ToolCall, result: ToolResult, agentId: string) => void,
  ): Promise<AgentResult> {
    try {
      if (signal?.aborted) {
        return { status: 'aborted', agentId: 'orchestrator' }
      }

      const projectRoot = process.cwd()
      const sessionKey = this.getSessionKey('orchestrator', projectRoot)

      // Reuse existing session to preserve conversation history, or create a fresh one.
      let session: Session | undefined = this.sessions.get(sessionKey)
      if (!session) {
        session = this.createSession('orchestrator', projectRoot)
        this.sessions.set(sessionKey, session)
      }

      // Append new user message to existing history from the session.
      const messages = [...(session.messages as typeof session.messages), { role: 'user' as const, content: request }]

      const ctx = {
        sessionId: session.id,
        agentId: 'orchestrator',
        cwd: session.projectRoot,
        allowedPaths:
          this.config.security?.allowedPaths ?? [session.projectRoot],
        onToolStart,
        onToolFinish,
      }

      const result = await runAgentLoop({
        agent: this.orchestratorAgent,
        messages,
        registry: this.registry,
        ctx,
        llm: this.llm,
        memory: session.stm,
        maxIterations: this.config.runtime?.maxIterations,
        maxToolRetries: this.config.runtime?.maxToolRetries,
        compressionRatio: this.config.runtime?.compressionRatio,
        contextWindow: this.orchestratorAgent.contextWindow,
        signal,
        onChunk,
        onToolStart,
        onToolFinish,
      })

      // Persist updated messages and STM back to the session for next run.
      if (result.status !== 'aborted') {
        session.messages = result.messages ?? []
        if (result.memory) {
          session.stm = result.memory
        }
      }

      return result
    } catch (e) {
      const msg = e instanceof Error ? (e.message || e.toString()) : typeof e === 'string' ? e : JSON.stringify(e)
      this.logger.error('Platform run failed', { error: msg })
      return {
        status: 'failed',
        agentId: 'orchestrator',
        error: msg,
      }
    }
  }
}
