import type {
  ChatMessage,
  ChatResponse,
  Logger,
  TokenUsage,
  ToolDefinition,
  ToolCall,
  LlmConfig,
} from '@agent-platform/shared-types'
import { consoleLogger } from '@agent-platform/shared-types'
import type { LLMAdapter } from './ClaudeAdapter.js'

function isAbortError(e: unknown): boolean {
  return e instanceof DOMException && e.name === 'AbortError'
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

const FINISH_REASON_MAP: Record<string, 'stop' | 'tool_calls' | 'length' | 'content_filter'> = {
  stop: 'stop',
  tool_calls: 'tool_calls',
  length: 'length',
  content_filter: 'content_filter',
}

/**
 * Check if a string appears to be a balanced JSON object (braces matched, respecting strings).
 * This is used to detect when accumulated SSE chunks form a complete JSON payload.
 */
function isBalancedJson(str: string): boolean {
  let depth = 0
  let inString = false
  let escapeNext = false

  for (let i = 0; i < str.length; i++) {
    const ch = str[i]

    if (escapeNext) {
      escapeNext = false
      continue
    }

    if (ch === '\\') {
      if (inString) escapeNext = true
      continue
    }

    if (ch === '"') {
      inString = !inString
      continue
    }

    if (!inString) {
      if (ch === '{' || ch === '[') depth++
      else if (ch === '}' || ch === ']') {
        depth--
        if (depth < 0) return false
      }
    }
  }

  return depth === 0 && !inString
}

/**
 * Safely parse a JSON string, returning the parsed value or undefined on failure.
 */
function safeJsonParse(str: string): unknown | undefined {
  try {
    return JSON.parse(str)
  } catch {
    return undefined
  }
}

export class OpenAIAdapter implements LLMAdapter {
  private apiKey?: string
  private baseUrl: string
  private timeoutSec: number
  private stream: boolean
  private fetchFn: typeof fetch
  private model: string
  private maxTokens: number
  private temperature: number
  private logger: Logger

  constructor(
    config: LlmConfig,
    options: { fetchFn?: typeof fetch; model?: string; maxTokens?: number; temperature?: number; logger?: Logger } = {},
  ) {
    this.apiKey = config.apiKey
    const raw = (config.baseUrl ?? 'https://api.openai.com/v1').replace(/\/+$/, '')
    this.baseUrl = raw.endsWith('/v1') ? raw : `${raw}/v1`
    this.timeoutSec = config.timeoutSec ?? 30
    this.stream = config.stream ?? true
    this.fetchFn = options.fetchFn ?? globalThis.fetch
    this.model = options.model ?? 'gpt-4o'
    this.maxTokens = options.maxTokens ?? 8192
    this.temperature = options.temperature ?? 0.2
    this.logger = options.logger ?? consoleLogger
  }

  async complete(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
    onChunk?: (text: string) => void,
  ): Promise<ChatResponse> {
    return this.completeWithRetry(messages, tools, onChunk)
  }

  private async completeWithRetry(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
    onChunk?: (text: string) => void,
    attempt = 0,
  ): Promise<ChatResponse> {
    const maxRetries = 2

    try {
      return await this.completeOnce(messages, tools, onChunk)
    } catch (e) {
      const isRetryable =
        e instanceof Error &&
        (isAbortError(e) ||
          /^OpenAI API error \((429|502|503)\)/.test(e.message))

      if (isRetryable && attempt < maxRetries) {
        const delay = Math.min(1000 * 2 ** attempt, 5000)
        this.logger.warn('API error, will retry', { status: e instanceof Error ? e.message : 'unknown', attempt })
        await sleep(delay)
        return this.completeWithRetry(messages, tools, onChunk, attempt + 1)
      }

      if (!(e instanceof Error)) throw e
      if (!/^OpenAI API error/.test(e.message)) {
        throw new Error(`OpenAI API call failed: ${e.message}`, { cause: e })
      }
      throw e
    }
  }

  private buildRequest(messages: ChatMessage[], tools?: ToolDefinition[]) {
    const oaiMessages = messages.map((m) => {
      if (m.role === 'assistant' && m.toolCalls && m.toolCalls.length > 0) {
        return {
          role: 'assistant' as const,
          content: m.content || null,
          tool_calls: m.toolCalls.map((tc) => ({
            id: tc.id,
            type: 'function' as const,
            function: {
              name: tc.name,
              arguments: JSON.stringify(tc.arguments),
            },
          })),
        }
      }
      if (m.role === 'tool') {
        return {
          role: 'tool' as const,
          tool_call_id: m.toolResults?.[0]?.toolCallId ?? '',
          content: m.content,
        }
      }
      return { role: m.role as 'system' | 'user' | 'assistant', content: m.content }
    })

    const body: Record<string, unknown> = {
      model: this.model,
      messages: oaiMessages,
      max_tokens: this.maxTokens,
      temperature: this.temperature,
    }

    if (this.stream) {
      body.stream = true
      body.stream_options = { include_usage: true }
    }

    if (tools && tools.length > 0) {
      body.tools = tools.map((t) => ({
        type: 'function' as const,
        function: {
          name: t.name,
          description: t.description,
          parameters: t.parameters,
        },
      }))
    }

    const headers: Record<string, string> = {
      'content-type': 'application/json',
    }
    if (this.apiKey) {
      headers['authorization'] = `Bearer ${this.apiKey}`
    }

    return body
  }

  private async completeOnce(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
    onChunk?: (text: string) => void,
  ): Promise<ChatResponse> {
    const body = this.buildRequest(messages, tools)

    const headers: Record<string, string> = {}
    if (this.apiKey) {
      headers['authorization'] = `Bearer ${this.apiKey}`
    }

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutSec * 1000)

    try {
      const response = await this.fetchFn(`${this.baseUrl}/chat/completions`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', ...headers },
        body: JSON.stringify(body),
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

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
        throw new Error(`OpenAI API error (${response.status}): ${errorMsg}`)
      }

      if (this.stream && response.body) {
        return this.parseStream(response, onChunk)
      }

      return this.parseResponse(await response.json())
    } catch (e) {
      clearTimeout(timeoutId)
      throw e
    }
  }

  private async parseStream(
    response: Response,
    onChunk?: (text: string) => void,
  ): Promise<ChatResponse> {
    if (!response.body) {
      throw new Error('No response body for streaming')
    }
    const reader = response.body.getReader()
    try {
      const decoder = new TextDecoder()
      let buffer = ''

      let content = ''
      const toolCallsAccum: ToolCall[] = []
      let finishReason = ''
      let usage: Record<string, number> | undefined

      // Track accumulated argument strings per tool call index for incremental parsing
      const argBuffers = new Map<number, string>()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || trimmed.startsWith(':')) continue

          if (trimmed === 'data: [DONE]') continue

          if (trimmed.startsWith('data: ')) {
            try {
              const parsed = JSON.parse(trimmed.slice(6))

              if (parsed.usage) {
                usage = parsed.usage
              }

              const choice = parsed.choices?.[0]
              if (!choice) continue

              if (choice.finish_reason) {
                finishReason = choice.finish_reason
              }

              const delta = choice.delta
              if (!delta) continue

              if (delta.content) {
                content += delta.content
                onChunk?.(delta.content)
              }

              if (delta.tool_calls) {
                for (const tc of delta.tool_calls) {
                  const idx = tc.index as number
                  if (!toolCallsAccum[idx]) {
                    toolCallsAccum[idx] = {
                      id: (tc.id as string) || '',
                      name: (tc.function?.name as string) || '',
                      arguments: '',
                    }
                    argBuffers.set(idx, '')
                  }

                  if (tc.function?.arguments) {
                    const buf = argBuffers.get(idx) ?? ''
                    const newBuf = buf + tc.function.arguments
                    argBuffers.set(idx, newBuf)
                    ;(toolCallsAccum[idx].arguments as string) += tc.function.arguments as string

                    // Try incremental parse when braces appear balanced
                    if (isBalancedJson(newBuf)) {
                      const parsedArgs = safeJsonParse(newBuf)
                      if (parsedArgs !== undefined && typeof parsedArgs === 'object') {
                        toolCallsAccum[idx].arguments = parsedArgs as Record<string, unknown>
                      }
                    }
                  }
                }
              }
            } catch {
              // skip malformed JSON in SSE
            }
          }
        }
      }

      const parsedToolCalls = toolCallsAccum.length > 0
        ? toolCallsAccum.map((tc) => {
            let args: unknown = tc.arguments

            if (typeof tc.arguments === 'string' && tc.arguments) {
              // Final parse attempt with balanced-brace check for safety
              const parsedArgs = safeJsonParse(tc.arguments as string)
              if (parsedArgs !== undefined && typeof parsedArgs === 'object') {
                args = parsedArgs
              } else if (isBalancedJson(tc.arguments as string)) {
                // Braces are balanced but parse failed — likely trailing comma or other issue; still try once more
                const fallback = safeJsonParse(tc.arguments as string)
                if (fallback !== undefined && typeof fallback === 'object') {
                  args = fallback
                } else {
                  args = {}
                }
              } else {
                // Braces not balanced — partial JSON from SSE split; fall back to empty object.
                args = {}
              }
            }

            return { ...tc, arguments: args }
          })
        : undefined

      return {
        message: {
          role: 'assistant',
          content: content || undefined,
          toolCalls: parsedToolCalls,
        },
        usage: {
          promptTokens: usage?.prompt_tokens ?? 0,
          completionTokens: usage?.completion_tokens ?? 0,
          totalTokens: usage?.total_tokens ?? 0,
        },
        finishReason: FINISH_REASON_MAP[finishReason] ?? 'stop',
      }
    } finally {
      reader.releaseLock()
    }
  }

  private parseResponse(result: Record<string, unknown>): ChatResponse {
    const choice = (result.choices as Array<Record<string, unknown>>)?.[0]
    const msg = choice?.message as Record<string, unknown> | undefined

    let content: string | undefined
    let toolCalls: ToolCall[] | undefined

    if (msg) {
      if (typeof msg.content === 'string' && msg.content) {
        content = msg.content
      }

      const rawToolCalls = msg.tool_calls as Array<Record<string, unknown>> | undefined
      if (rawToolCalls && rawToolCalls.length > 0) {
        toolCalls = rawToolCalls.map((tc) => {
          const fn = tc.function as Record<string, unknown> | undefined
          let args: unknown = {}
          if (fn?.arguments) {
            try {
              args = JSON.parse(fn.arguments as string)
            } catch {
              // malformed arguments — fall back to empty object
            }
          }
          return {
            id: tc.id as string,
            name: fn?.name as string,
            arguments: args,
          }
        })
      }
    }

    const usage = result.usage as Record<string, number> | undefined
    const tokenUsage: TokenUsage = {
      promptTokens: usage?.prompt_tokens ?? 0,
      completionTokens: usage?.completion_tokens ?? 0,
      totalTokens: usage?.total_tokens ?? 0,
    }

    const finishReason = choice?.finish_reason as string

    return {
      message: {
        role: 'assistant',
        content: content,
        toolCalls,
      },
      usage: tokenUsage,
      finishReason: FINISH_REASON_MAP[finishReason] ?? 'stop',
    }
  }
}
