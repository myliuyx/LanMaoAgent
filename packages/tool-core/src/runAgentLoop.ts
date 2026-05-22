import type {
  Agent,
  AgentResult,
  ChatMessage,
  ToolCall,
  ToolResult,
  ToolExecutionContext,
} from '@agent-platform/shared-types'
import type { LLMAdapter } from '@agent-platform/llm-adapter'
import { ShortTermMemory } from '@agent-platform/memory-stm'
import type { ToolRegistry } from './ToolRegistry.js'

export interface AgentLoopConfig {
  agent: Agent
  messages: ChatMessage[]
  registry: ToolRegistry
  ctx: ToolExecutionContext
  llm: LLMAdapter
  memory?: ShortTermMemory
  maxIterations?: number
  maxToolRetries?: number
  contextWindow?: number
  compressionRatio?: number
  signal?: AbortSignal
  onChunk?: (text: string) => void
  onToolStart?: (call: ToolCall, agentId: string) => void
  onToolFinish?: (call: ToolCall, result: ToolResult, agentId: string) => void
  onToolRetry?: (call: ToolCall, attempt: number, maxAttempts: number, error: string, agentId: string) => void
  depth?: number
  maxDepth?: number
}

export interface AgentLoopResult extends AgentResult {
  messages: ChatMessage[]
  memory?: ShortTermMemory
}

/** Rough token count estimate from character length. */
function estimateTokens(text: string): number {
  return new TextEncoder().encode(text).length / 3.5
}

/** Estimate total tokens that will be sent to the LLM this iteration (system + all messages). */
function estimateLLMTokens(
  systemPrompt: string,
  msgs: ChatMessage[],
): number {
  let total = estimateTokens(systemPrompt)
  for (const m of msgs) {
    if (m.content) total += estimateTokens(m.content)
    if (m.toolCalls) {
      for (const tc of m.toolCalls) {
        total += estimateTokens(JSON.stringify(tc))
      }
    }
    if (m.toolResults) {
      for (const tr of m.toolResults) {
        total += estimateTokens(tr.content || '')
      }
    }
  }
  return total
}

export async function runAgentLoop(
  config: AgentLoopConfig,
): Promise<AgentLoopResult> {
  const maxIterations = config.maxIterations ?? 20
  let messages = [...config.messages]

  // Check delegation depth limit
  if ((config.depth ?? 0) >= (config.maxDepth ?? 5)) {
    return {
      status: 'failed' as const,
      agentId: config.agent.id,
      error: 'Max delegation depth exceeded',
      messages: [...config.messages],
      memory: config.memory,
    }
  }

  for (let iteration = 0; iteration < maxIterations; iteration++) {
    if (config.signal?.aborted) {
      return { status: 'aborted', agentId: config.agent.id, messages, memory: config.memory }
    }

    const systemPrompt = config.agent.systemPrompt
    const contextSystemMessages = messages.filter((m) => m.role === 'system')
    const restMessages = messages.filter((m) => m.role !== 'system')
    const tools = config.agent.tools.flatMap((h) => h.getTools())

    let response
    try {
      response = await config.llm.complete(
        [
          { role: 'system', content: systemPrompt },
          ...contextSystemMessages,
          ...restMessages,
        ],
        tools,
        config.onChunk,
      )
    } catch (e) {
      const msg = e instanceof Error ? (e.message || e.toString()) : typeof e === 'string' ? e : JSON.stringify(e)
      return {
        status: 'failed' as const,
        agentId: config.agent.id,
        error: `LLM API call failed: ${msg}`,
        messages,
        memory: config.memory,
      }
    }

    const toolCalls = response.message.toolCalls as ToolCall[] | undefined

    if (!toolCalls || toolCalls.length === 0) {
      return {
        status: 'completed',
        output: response.message.content,
        agentId: config.agent.id,
        messages,
        memory: config.memory,
      }
    }

    // Record start index before pushing new messages so STM sync is robust.
    const newMsgStart = messages.length

    messages.push({
      role: 'assistant' as const,
      content: response.message.content ?? '',
      toolCalls,
    })

    for (const call of toolCalls) {
      config.onToolStart?.(call, config.agent.id)
      const maxRetries = config.maxToolRetries ?? 2
      let result: ToolResult
      let attempt = 1
      for (;;) {
        result = await config.registry.execute(call, config.ctx)
        if (!result.isError) break
        if (result.retryable === false) break
        if (attempt > maxRetries) break
        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 4000)
        // Check signal before waiting to avoid unnecessary delays after abort
        if (config.signal?.aborted) break
        await new Promise<void>(r => {
          const timeoutId = setTimeout(r, delay)
          if (config.signal?.aborted) { clearTimeout(timeoutId); return }
        })
        config.onToolRetry?.(call, attempt, maxRetries, result.content, config.agent.id)
        attempt++
      }
      config.onToolFinish?.(call, result, config.agent.id)
      messages.push({
        role: 'tool' as const,
        content: result.content,
        toolResults: [{ content: result.content, isError: result.isError, toolCallId: call.id }],
      })
    }

    if (config.memory) {
      // Sync new messages to STM using the recorded start index.
      for (let i = newMsgStart; i < messages.length; i++) {
        config.memory.add(messages[i])
      }

      const budget = Math.floor(
        (config.contextWindow ?? config.agent.contextWindow ?? 200000) *
          (config.compressionRatio ?? 0.7),
      )

      // Trigger compact when current context exceeds budget.
      const llmTokenEstimate = estimateLLMTokens(systemPrompt, messages)
      const needsCompact = llmTokenEstimate > budget

      if (needsCompact) {
        const freed = config.memory.compact()

        if (freed > 0) {
          // Rebuild STM from the unified array so future adds stay in sync.
          const stmContext = config.memory.getContext()
          const keepCount = (toolCalls?.length ?? 0) + 1
          const recent = messages.splice(-keepCount)
          messages = [...stmContext, ...recent]

          config.memory = new ShortTermMemory(0, 50)
          for (const m of messages) {
            config.memory.add(m)
          }
        }
      }
    }
  }

  return { status: 'max_iterations_reached', agentId: config.agent.id, error: 'Max iterations reached', messages, memory: config.memory }
}
