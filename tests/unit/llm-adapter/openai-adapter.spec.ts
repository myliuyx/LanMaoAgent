import { describe, it, expect, vi } from 'vitest'
import { OpenAIAdapter } from '@agent-platform/llm-adapter'
import type { ToolDefinition } from '@agent-platform/shared-types'

const API_KEY = 'sk-test-123'

function makeFetch(body?: unknown) {
  const defaultBody = {
    choices: [
      {
        message: { content: 'Hello!', role: 'assistant' },
        finish_reason: 'stop',
      },
    ],
    usage: { prompt_tokens: 10, completion_tokens: 20, total_tokens: 30 },
  }
  return vi.fn<Parameters<typeof fetch>>().mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve(body ?? defaultBody),
  } as Response)
}

function makeStreamFetch(
  chunks: string[],
): ReturnType<typeof vi.fn> {
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk))
      }
      controller.close()
    },
  })
  return vi.fn<Parameters<typeof fetch>>().mockResolvedValue({
    ok: true,
    status: 200,
    body: stream,
  } as Response)
}

const toolDefs: ToolDefinition[] = [
  {
    name: 'read_file',
    description: 'Read a file from disk',
    parameters: {
      type: 'object',
      properties: { path: { type: 'string' } },
      required: ['path'],
    },
  },
]

describe('OpenAIAdapter', () => {
  describe('non-streaming requests', () => {
    it('parses basic text response', async () => {
      const fetchFn = makeFetch()
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      const result = await adapter.complete([
        { role: 'user', content: 'Hello' },
      ])
      expect(result.message.role).toBe('assistant')
      expect(result.message.content).toBe('Hello!')
      expect(result.finishReason).toBe('stop')
    })

    it('parses token usage correctly', async () => {
      const fetchFn = makeFetch()
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      const result = await adapter.complete([
        { role: 'user', content: 'Hi' },
      ])
      expect(result.usage.promptTokens).toBe(10)
      expect(result.usage.completionTokens).toBe(20)
      expect(result.usage.totalTokens).toBe(30)
    })

    it('parses tool_calls finish reason', async () => {
      const body = {
        choices: [
          {
            message: {
              content: null,
              role: 'assistant',
              tool_calls: [
                {
                  id: 'call_1',
                  type: 'function',
                  function: {
                    name: 'read_file',
                    arguments: JSON.stringify({ path: '/tmp/test.txt' }),
                  },
                },
              ],
            },
            finish_reason: 'tool_calls',
          },
        ],
        usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
      }
      const fetchFn = makeFetch(body)
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      const result = await adapter.complete(
        [{ role: 'user', content: 'Read file' }],
        toolDefs,
      )
      expect(result.finishReason).toBe('tool_calls')
      expect(result.message.toolCalls).toHaveLength(1)
      expect(result.message.toolCalls![0].name).toBe('read_file')
      expect(result.message.toolCalls![0].arguments).toEqual({
        path: '/tmp/test.txt',
      })
    })

    it('builds request body with tools', async () => {
      const fetchFn = makeFetch()
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      await adapter.complete(
        [{ role: 'user', content: 'Do something' }],
        toolDefs,
      )
      const [, req] = fetchFn.mock.calls[0]
      const body = JSON.parse(req!.body as string)
      expect(body.tools).toHaveLength(1)
      expect(body.tools[0].type).toBe('function')
      expect(body.tools[0].function.name).toBe('read_file')
    })

    it('includes stream flag in request by default', async () => {
      const fetchFn = makeFetch()
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      await adapter.complete([{ role: 'user', content: 'Hi' }])
      const [, req] = fetchFn.mock.calls[0]
      const body = JSON.parse(req!.body as string)
      expect(body.stream).toBe(true)
    })
  })

  describe('streaming responses', () => {
    it('parses streaming text response', async () => {
      const fetchFn = makeStreamFetch([
        'data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}\n\n',
        'data: {"choices":[{"delta":{"content":" world"},"finish_reason":null}]}\n\n',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n',
        'data: [DONE]\n\n',
      ])
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      const result = await adapter.complete([
        { role: 'user', content: 'Hi' },
      ])
      expect(result.message.content).toBe('Hello world')
      expect(result.finishReason).toBe('stop')
    })

    it('parses streaming tool calls', async () => {
      const fetchFn = makeStreamFetch([
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","function":{"name":"read_file","arguments":""}}]},"finish_reason":null}]}\n\n',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\\"path\\":"}}]},"finish_reason":null}]}\n\n',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":" \\"/tmp/test.txt\\"}"}}]},"finish_reason":null}]}\n\n',
        'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}\n\n',
        'data: [DONE]\n\n',
      ])
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      const result = await adapter.complete(
        [{ role: 'user', content: 'Read file' }],
        toolDefs,
      )
      expect(result.finishReason).toBe('tool_calls')
      expect(result.message.toolCalls).toHaveLength(1)
      expect(result.message.toolCalls![0].name).toBe('read_file')
      expect(result.message.toolCalls![0].id).toBe('call_1')
      expect(result.message.toolCalls![0].arguments).toEqual({
        path: '/tmp/test.txt',
      })
    })

    it('invokes onChunk callback during streaming', async () => {
      const fetchFn = makeStreamFetch([
        'data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}\n\n',
        'data: {"choices":[{"delta":{"content":" world"},"finish_reason":null}]}\n\n',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n',
        'data: [DONE]\n\n',
      ])
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      const chunks: string[] = []
      const result = await adapter.complete(
        [{ role: 'user', content: 'Hi' }],
        undefined,
        (chunk) => { chunks.push(chunk) },
      )
      expect(chunks).toEqual(['Hello', ' world'])
      expect(result.message.content).toBe('Hello world')
    })

    it('handles streaming with usage info', async () => {
      const fetchFn = makeStreamFetch([
        'data: {"choices":[{"delta":{"content":"Done"},"finish_reason":null}]}\n\n',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":3,"total_tokens":8}}\n\n',
        'data: [DONE]\n\n',
      ])
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      const result = await adapter.complete([
        { role: 'user', content: 'Hi' },
      ])
      expect(result.message.content).toBe('Done')
      expect(result.usage.totalTokens).toBe(8)
    })
  })

  describe('error handling and retries', () => {
    it('429 triggers retry then succeeds', async () => {
      let callCount = 0
      const fetchFn = vi.fn<Parameters<typeof fetch>>().mockImplementation(() => {
        callCount++
        if (callCount < 3) {
          return Promise.resolve({
            ok: false,
            status: 429,
            json: () =>
              Promise.resolve({
                error: { message: 'Rate limited' },
              }),
          } as Response)
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              choices: [
                {
                  message: { content: 'Success', role: 'assistant' },
                  finish_reason: 'stop',
                },
              ],
              usage: { prompt_tokens: 5, completion_tokens: 5, total_tokens: 10 },
            }),
        } as Response)
      })
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      const result = await adapter.complete([
        { role: 'user', content: 'Hi' },
      ])
      expect(result.message.content).toBe('Success')
      expect(fetchFn).toHaveBeenCalledTimes(3)
    })

    it('non-retryable error (400) does not retry', async () => {
      const fetchFn = vi.fn<Parameters<typeof fetch>>().mockResolvedValue({
        ok: false,
        status: 400,
        json: () =>
          Promise.resolve({
            error: { message: 'Bad request' },
          }),
      } as Response)
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      await expect(
        adapter.complete([{ role: 'user', content: 'Hi' }]),
      ).rejects.toThrow('OpenAI API error (400): Bad request')
      expect(fetchFn).toHaveBeenCalledTimes(1)
    })

    it('network timeout triggers retry then succeeds', async () => {
      let callCount = 0
      const fetchFn = vi.fn<Parameters<typeof fetch>>().mockImplementation(() => {
        callCount++
        if (callCount < 2) {
          return Promise.reject(
            new DOMException('The operation was aborted', 'AbortError'),
          )
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              choices: [
                {
                  message: { content: 'Success', role: 'assistant' },
                  finish_reason: 'stop',
                },
              ],
              usage: { prompt_tokens: 5, completion_tokens: 5, total_tokens: 10 },
            }),
        } as Response)
      })
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      const result = await adapter.complete([
        { role: 'user', content: 'Hi' },
      ])
      expect(result.message.content).toBe('Success')
      expect(fetchFn).toHaveBeenCalledTimes(2)
    })

    it('non-abort network error fails without retry', async () => {
      const fetchFn = vi
        .fn<Parameters<typeof fetch>>()
        .mockRejectedValue(new Error('DNS resolution failed'))
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      await expect(
        adapter.complete([{ role: 'user', content: 'Hi' }]),
      ).rejects.toThrow('OpenAI API call failed: DNS resolution failed')
      expect(fetchFn).toHaveBeenCalledTimes(1)
    })
  })

  describe('request configuration', () => {
    it('uses custom baseUrl', async () => {
      const fetchFn = makeFetch()
      const adapter = new OpenAIAdapter(
        {
          provider: 'openai',
          apiKey: API_KEY,
          baseUrl: 'https://custom.openai.com',
        },
        { fetchFn },
      )
      await adapter.complete([{ role: 'user', content: 'Hi' }])
      const [url] = fetchFn.mock.calls[0]
      expect(url).toBe('https://custom.openai.com/v1/chat/completions')
    })

    it('sets authorization header when apiKey is provided', async () => {
      const fetchFn = makeFetch()
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      await adapter.complete([{ role: 'user', content: 'Hi' }])
      const [, req] = fetchFn.mock.calls[0]
      const headers = req!.headers as Record<string, string>
      expect(headers.authorization).toBe(`Bearer ${API_KEY}`)
    })

    it('works without apiKey', async () => {
      const fetchFn = makeFetch()
      const adapter = new OpenAIAdapter(
        { provider: 'openai' },
        { fetchFn },
      )
      await adapter.complete([{ role: 'user', content: 'Hi' }])
      const [, req] = fetchFn.mock.calls[0]
      const headers = req!.headers as Record<string, string>
      expect(headers.authorization).toBeUndefined()
    })

    it('disables streaming when config.stream is false', async () => {
      const fetchFn = makeFetch()
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY, stream: false },
        { fetchFn },
      )
      await adapter.complete([{ role: 'user', content: 'Hi' }])
      const [, req] = fetchFn.mock.calls[0]
      const body = JSON.parse(req!.body as string)
      expect(body.stream).toBeUndefined()
    })
  })

  describe('tool message conversion', () => {
    it('maps tool role messages with tool_call_id', async () => {
      const fetchFn = makeFetch()
      const adapter = new OpenAIAdapter(
        { provider: 'openai', apiKey: API_KEY },
        { fetchFn },
      )
      await adapter.complete([
        {
          role: 'assistant',
          content: '',
          toolCalls: [
            { id: 'call_1', name: 'read_file', arguments: { path: '/tmp/x' } },
          ],
        },
        {
          role: 'tool',
          content: 'file content',
          toolResults: [{ content: 'file content', isError: false, toolCallId: 'call_1' }],
        },
      ])
      const [, req] = fetchFn.mock.calls[0]
      const body = JSON.parse(req!.body as string)
      const toolMsg = body.messages.find(
        (m: { role: string }) => m.role === 'tool',
      )
      expect(toolMsg).toBeDefined()
      expect(toolMsg.tool_call_id).toBe('call_1')
      expect(toolMsg.content).toBe('file content')
    })
  })
})
