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
}

export async function runAgentLoop(
  config: AgentLoopConfig,
): Promise<AgentLoopResult> {
  // Check delegation depth limit
  if ((config.depth ?? 0) >= (config.maxDepth ?? 5)) {
    return {
      status: 'failed' as const,
      agentId: config.agent.id,
      error: 'Max delegation depth exceeded',
      messages: [...config.messages],
    }
  }

  const maxIterations = config.maxIterations ?? 20
  let messages = [...config.messages]
  let totalTokens = 0
  let consecutiveCompactFailures = 0

  const contextWindow = config.contextWindow ?? config.agent.contextWindow ?? 200000
  const compressionRatio = config.compressionRatio ?? 0.7
  const budget = Math.floor(contextWindow * compressionRatio)

  for (let iteration = 0; iteration < maxIterations; iteration++) {
    if (config.signal?.aborted) {
      return { status: 'aborted', agentId: config.agent.id, messages }
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
      }
    }

    const toolCalls = response.message.toolCalls as ToolCall[] | undefined

    if (!toolCalls || toolCalls.length === 0) {
      return {
        status: 'completed',
        output: response.message.content,
        agentId: config.agent.id,
        messages,
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

      totalTokens += response.usage.totalTokens

      if (totalTokens > budget * 2 && consecutiveCompactFailures >= 3) {
        return {
          status: 'failed',
          agentId: config.agent.id,
          error: 'Token budget exceeded hard limit',
          messages,
        }
      }

      if (totalTokens > budget) {
        const freed = config.memory.compact()
        if (freed > 0) {
          totalTokens = Math.max(0, totalTokens - freed)
          consecutiveCompactFailures = 0

          // 将 STM 压缩后的消息同步回 local messages，并重建 STM 使两者保持一致。
          const stmContext = config.memory.getContext()
          const keepCount = toolCalls.length + 1
          const recent = messages.splice(-keepCount)
          messages = [...stmContext, ...recent]

          // Rebuild STM from the unified array so future adds stay in sync.
          config.memory = new ShortTermMemory(0, 50)
          for (const m of messages) {
            config.memory.add(m)
          }
        } else {
          consecutiveCompactFailures++
          if (consecutiveCompactFailures >= 3) {
            return {
              status: 'failed',
              agentId: config.agent.id,
              error: 'Token budget exceeded hard limit',
              messages,
            }
          }
        }
      }
    }
  }

  return { status: 'max_iterations_reached', agentId: config.agent.id, error: 'Max iterations reached', messages }
}
