import type {
  ChatMessage,
  ChatResponse,
  TokenUsage,
  ToolDefinition,
  ToolCall,
  LlmConfig,
} from '@agent-platform/shared-types'

export interface LLMAdapter {
  complete(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
    onChunk?: (text: string) => void,
  ): Promise<ChatResponse>
}

interface ClaudeAdapterOptions {
  fetchFn?: typeof fetch
  model?: string
  maxTokens?: number
  temperature?: number
}

function isAbortError(e: unknown): boolean {
  return e instanceof DOMException && e.name === 'AbortError'
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export class ClaudeAdapter implements LLMAdapter {
  private apiKey: string
  private baseUrl: string
  private timeoutSec: number
  private fetchFn: typeof fetch
  private model: string
  private maxTokens: number
  private temperature: number

  constructor(
    config: LlmConfig,
    options: ClaudeAdapterOptions = {},
  ) {
    if (!config.apiKey) {
      throw new Error('apiKey required for Anthropic provider')
    }
    this.apiKey = config.apiKey
    this.baseUrl = (config.baseUrl ?? 'https://api.anthropic.com').replace(
      /\/+$/,
      '',
    )
    this.timeoutSec = config.timeoutSec ?? 30
    this.fetchFn = options.fetchFn ?? globalThis.fetch
    this.model = options.model ?? 'claude-sonnet-4-20250514'
    this.maxTokens = options.maxTokens ?? 8192
    this.temperature = options.temperature ?? 0.2
  }

  async complete(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
    _onChunk?: (text: string) => void,
  ): Promise<ChatResponse> {
    return this.completeWithRetry(messages, tools)
  }

  private async completeWithRetry(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
    attempt = 0,
  ): Promise<ChatResponse> {
    const maxRetries = 2

    try {
      return await this.completeOnce(messages, tools)
    } catch (e) {
      const isRetryable =
        e instanceof Error &&
        (isAbortError(e) ||
          /^Anthropic API error \((429|502|503)\)/.test(e.message))

      if (isRetryable && attempt < maxRetries) {
        const delay = Math.min(1000 * 2 ** attempt, 5000)
        await sleep(delay)
        return this.completeWithRetry(messages, tools, attempt + 1)
      }

      if (!(e instanceof Error)) throw e
      if (!/^Anthropic API error/.test(e.message)) {
        throw new Error(`Anthropic API call failed: ${e.message}`, { cause: e })
      }
      throw e
    }
  }

  private async completeOnce(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
  ): Promise<ChatResponse> {
    const systemMsgs = messages.filter((m) => m.role === 'system')
    const system = systemMsgs.map((m) => m.content).join('\n')

    const anthropicMessages = messages
      .filter((m) => m.role !== 'system')
      .map((m) => {
        if (m.role === 'tool') {
          return { role: 'user' as const, content: m.content }
        }
        if (m.role === 'assistant' && m.toolCalls && m.toolCalls.length > 0) {
          const content: unknown[] = []
          if (m.content) {
            content.push({ type: 'text' as const, text: m.content })
          }
          for (const tc of m.toolCalls) {
            content.push({
              type: 'tool_use' as const,
              id: tc.id,
              name: tc.name,
              input: tc.arguments,
            })
          }
          return { role: 'assistant' as const, content }
        }
        return { role: m.role as 'user' | 'assistant', content: m.content }
      })

    const body: Record<string, unknown> = {
      model: this.model,
      max_tokens: this.maxTokens,
      temperature: this.temperature,
      messages: anthropicMessages,
    }
    if (system) body.system = system

    if (tools && tools.length > 0) {
      body.tools = tools.map((t) => ({
        name: t.name,
        description: t.description,
        input_schema: t.parameters,
      }))
    }

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutSec * 1000)

    try {
      const url = `${this.baseUrl}/v1/messages`
      const response = await this.fetchFn(url, {
        method: 'POST',
        headers: {
          'x-api-key': this.apiKey,
          'anthropic-version': '2023-06-01',
          'content-type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      })

      if (!response.ok) {
        let errorMsg = `HTTP ${response.status}`
        try {
          const errBody = await response.json()
          if (errBody?.error?.message) {
            errorMsg = errBody.error.message
          }
        } catch {
          // ignore parse errors
        }
        throw new Error(
          `Anthropic API error (${response.status}): ${errorMsg}`,
        )
      }

      const result = await response.json()
      return this.parseResponse(result)
    } finally {
      clearTimeout(timeoutId)
    }
  }

  private parseResponse(result: Record<string, unknown>): ChatResponse {
    let content = ''
    const toolCalls: ToolCall[] = []

    const contentBlocks = result.content as Array<Record<string, unknown>>
    if (contentBlocks) {
      for (const block of contentBlocks) {
        if (block.type === 'text') {
          content += block.text ?? ''
        } else if (block.type === 'tool_use') {
          toolCalls.push({
            id: block.id as string,
            name: block.name as string,
            arguments: block.input,
          })
        }
      }
    }

    const usage = result.usage as Record<string, number> | undefined
    const tokenUsage: TokenUsage = {
      promptTokens: usage?.input_tokens ?? 0,
      completionTokens: usage?.output_tokens ?? 0,
      totalTokens:
        (usage?.input_tokens ?? 0) + (usage?.output_tokens ?? 0),
    }

    const stopReason = result.stop_reason as string
    const finishReasonMap: Record<string, 'stop' | 'tool_calls' | 'length' | 'content_filter'> = {
      end_turn: 'stop',
      tool_use: 'tool_calls',
      max_tokens: 'length',
      content_filter: 'content_filter',
    }

    return {
      message: {
        role: 'assistant',
        content: content || undefined,
        toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
      },
      usage: tokenUsage,
      finishReason: finishReasonMap[stopReason] ?? 'stop',
    }
  }
}
