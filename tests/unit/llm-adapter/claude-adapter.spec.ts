import { describe, it, expect, vi } from 'vitest'
import { ClaudeAdapter } from '@agent-platform/llm-adapter'
import type { ChatMessage, ToolDefinition } from '@agent-platform/shared-types'

const API_KEY = 'sk-test-123'

function makeFetch(response: Partial<{
  ok: boolean
  status: number
  body: unknown
  statusText: string
}> = {}) {
  const { ok = true, status = 200, body, statusText } = response
  return vi.fn<Parameters<typeof fetch>>().mockResolvedValue({
    ok,
    status,
    statusText: statusText ?? 'OK',
    json: () =>
      Promise.resolve(
        body ?? {
          id: 'msg_01',
          type: 'message',
          role: 'assistant',
          content: [{ type: 'text', text: 'Hello!' }],
          model: 'claude-sonnet-4-20250514',
          stop_reason: 'end_turn',
          usage: { input_tokens: 10, output_tokens: 20 },
        },
      ),
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

describe('ClaudeAdapter', () => {
  describe('message conversion (Step 3.1)', () => {
    it('system messages go to system param, not messages array', async () => {
      const fetchFn = makeFetch()
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: API_KEY },
        { fetchFn },
      )
      const messages: ChatMessage[] = [
        { role: 'system', content: 'You are a helpful assistant.' },
        { role: 'user', content: 'Hello' },
      ]
      await adapter.complete(messages)
      const [, req] = fetchFn.mock.calls[0]
      const body = JSON.parse(req!.body as string)
      expect(body.system).toBe('You are a helpful assistant.')
      expect(body.messages).toHaveLength(1)
      expect(body.messages[0].role).toBe('user')
    })

    it('tools are converted to Anthropic format with JSON Schema input_schema', async () => {
      const fetchFn = makeFetch()
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: API_KEY },
        { fetchFn, model: 'claude-opus-4-20250514' },
      )
      await adapter.complete(
        [{ role: 'user', content: 'Read file' }],
        toolDefs,
      )
      const [, req] = fetchFn.mock.calls[0]
      const body = JSON.parse(req!.body as string)
      expect(body.tools).toHaveLength(1)
      expect(body.tools[0].name).toBe('read_file')
      expect(body.tools[0].description).toBe('Read a file from disk')
      expect(body.tools[0].input_schema).toEqual({
        type: 'object',
        properties: { path: { type: 'string' } },
        required: ['path'],
      })
    })

    it('response is parsed correctly: text content, token usage, finish reason', async () => {
      const fetchFn = makeFetch()
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: API_KEY },
        { fetchFn },
      )
      const result = await adapter.complete([
        { role: 'user', content: 'Hello' },
      ])
      expect(result.message.role).toBe('assistant')
      expect(result.message.content).toBe('Hello!')
      expect(result.usage.promptTokens).toBe(10)
      expect(result.usage.completionTokens).toBe(20)
      expect(result.usage.totalTokens).toBe(30)
      expect(result.finishReason).toBe('stop')
    })

    it('stop_reason tool_use maps to finishReason tool_calls', async () => {
      const fetchFn = vi.fn<Parameters<typeof fetch>>().mockResolvedValue({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            id: 'msg_02',
            type: 'message',
            role: 'assistant',
            content: [
              { type: 'text', text: 'I will read the file.' },
              {
                type: 'tool_use',
                id: 'toolu_01',
                name: 'read_file',
                input: { path: '/tmp/test.txt' },
              },
            ],
            stop_reason: 'tool_use',
            usage: { input_tokens: 10, output_tokens: 25 },
          }),
      } as Response)
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: API_KEY },
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

    it('includes anthropic-version header', async () => {
      const fetchFn = makeFetch()
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: API_KEY },
        { fetchFn },
      )
      await adapter.complete([{ role: 'user', content: 'Hello' }])
      const [, req] = fetchFn.mock.calls[0]
      expect(req!.headers).toMatchObject({
        'x-api-key': API_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
      })
    })

    it('uses custom baseUrl and timeoutSec', async () => {
      const fetchFn = makeFetch()
      const adapter = new ClaudeAdapter(
        {
          provider: 'anthropic',
          apiKey: API_KEY,
          baseUrl: 'https://custom.anthropic.com',
          timeoutSec: 30,
        },
        { fetchFn },
      )
      await adapter.complete([{ role: 'user', content: 'Hello' }])
      const [url, req] = fetchFn.mock.calls[0]
      expect(url).toBe('https://custom.anthropic.com/v1/messages')
      expect((req as RequestInit).signal).toBeDefined()
    })
  })

    it('converts tool messages to user messages in request', async () => {
      const fetchFn = makeFetch()
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: API_KEY },
        { fetchFn },
      )
      await adapter.complete([
        { role: 'assistant', content: 'Reading file...' },
        { role: 'tool', content: 'file content here' },
        { role: 'user', content: 'Thanks' },
      ])
      const [, req] = fetchFn.mock.calls[0]
      const body = JSON.parse(req!.body as string)
      expect(body.messages).toHaveLength(3)
      expect(body.messages[1].role).toBe('user')
      expect(body.messages[1].content).toBe('file content here')
    })

    it('converts assistant toolCalls to content array with tool_use blocks', async () => {
      const fetchFn = makeFetch()
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: API_KEY },
        { fetchFn },
      )
      await adapter.complete([
        {
          role: 'assistant',
          content: 'I will read the file.',
          toolCalls: [
            { id: 'tc_01', name: 'read_file', arguments: { path: '/tmp/test.txt' } },
          ],
        },
      ])
      const [, req] = fetchFn.mock.calls[0]
      const body = JSON.parse(req!.body as string)
      expect(Array.isArray(body.messages[0].content)).toBe(true)
      const blocks = body.messages[0].content
      expect(blocks[0].type).toBe('text')
      expect(blocks[0].text).toBe('I will read the file.')
      expect(blocks[1].type).toBe('tool_use')
      expect(blocks[1].id).toBe('tc_01')
      expect(blocks[1].name).toBe('read_file')
      expect(blocks[1].input).toEqual({ path: '/tmp/test.txt' })
    })

  describe('error handling (Step 3.2)', () => {
    it('400 returns error with code and message, no retry', async () => {
      const fetchFn = vi.fn<Parameters<typeof fetch>>().mockResolvedValue({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: () =>
          Promise.resolve({
            error: { type: 'invalid_request_error', message: 'Bad request' },
          }),
      } as Response)
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: API_KEY },
        { fetchFn },
      )
      await expect(
        adapter.complete([{ role: 'user', content: 'Hi' }]),
      ).rejects.toThrow('Anthropic API error (400): Bad request')
      expect(fetchFn).toHaveBeenCalledTimes(1)
    })

    it('401/403 indicates auth problem clearly, no retry', async () => {
      const fetchFn = vi.fn<Parameters<typeof fetch>>().mockResolvedValue({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: () =>
          Promise.resolve({
            error: { type: 'authentication_error', message: 'Invalid API key' },
          }),
      } as Response)
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: 'bad-key' },
        { fetchFn },
      )
      await expect(
        adapter.complete([{ role: 'user', content: 'Hi' }]),
      ).rejects.toThrow('Anthropic API error (401): Invalid API key')
      expect(fetchFn).toHaveBeenCalledTimes(1)
    })

    it('429 triggers retry then fails after maxRetries', async () => {
      const fetchFn = vi.fn<Parameters<typeof fetch>>().mockResolvedValue({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        json: () =>
          Promise.resolve({
            error: { type: 'rate_limit_error', message: 'Rate limited' },
          }),
      } as Response)
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: API_KEY },
        { fetchFn },
      )
      await expect(
        adapter.complete([{ role: 'user', content: 'Hi' }]),
      ).rejects.toThrow('Anthropic API error (429): Rate limited')
      expect(fetchFn.mock.calls.length).toBeGreaterThanOrEqual(2)
    })

    it('502/503 triggers retry with exponential backoff', async () => {
      let callCount = 0
      const fetchFn = vi.fn<Parameters<typeof fetch>>().mockImplementation(() => {
        callCount++
        if (callCount < 3) {
          return Promise.resolve({
            ok: false,
            status: 502,
            statusText: 'Bad Gateway',
            json: () =>
              Promise.resolve({
                error: { type: 'server_error', message: 'Bad Gateway' },
              }),
          } as Response)
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              id: 'msg_03',
              type: 'message',
              role: 'assistant',
              content: [{ type: 'text', text: 'Success after retry' }],
              stop_reason: 'end_turn',
              usage: { input_tokens: 10, output_tokens: 20 },
            }),
        } as Response)
      })
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: API_KEY },
        { fetchFn },
      )
      const result = await adapter.complete([
        { role: 'user', content: 'Hi' },
      ])
      expect(result.message.content).toBe('Success after retry')
      expect(fetchFn).toHaveBeenCalledTimes(3)
    })

    it('network timeout triggers retry', async () => {
      let callCount = 0
      const fetchFn = vi.fn<Parameters<typeof fetch>>().mockImplementation(() => {
        callCount++
        if (callCount < 3) {
          return Promise.reject(new DOMException('The operation was aborted', 'AbortError'))
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              id: 'msg_04',
              type: 'message',
              role: 'assistant',
              content: [{ type: 'text', text: 'Success' }],
              stop_reason: 'end_turn',
              usage: { input_tokens: 10, output_tokens: 20 },
            }),
        } as Response)
      })
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: API_KEY },
        { fetchFn },
      )
      const result = await adapter.complete([
        { role: 'user', content: 'Hi' },
      ])
      expect(result.message.content).toBe('Success')
      expect(fetchFn).toHaveBeenCalledTimes(3)
    })

    it('non-abort network error fails without retry', async () => {
      const fetchFn = vi.fn<Parameters<typeof fetch>>().mockRejectedValue(
        new Error('DNS resolution failed'),
      )
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: API_KEY },
        { fetchFn },
      )
      await expect(
        adapter.complete([{ role: 'user', content: 'Hi' }]),
      ).rejects.toThrow('Anthropic API call failed: DNS resolution failed')
      expect(fetchFn).toHaveBeenCalledTimes(1)
    })

    it('success on first try skips retry', async () => {
      const fetchFn = makeFetch()
      const adapter = new ClaudeAdapter(
        { provider: 'anthropic', apiKey: API_KEY },
        { fetchFn },
      )
      await adapter.complete([{ role: 'user', content: 'Hi' }])
      expect(fetchFn).toHaveBeenCalledTimes(1)
    })
  })
})
