import { describe, it, expect, vi } from 'vitest'
import type { ChatMessage, ChatResponse } from '@agent-platform/shared-types'

const standardMessages: ChatMessage[] = [
  { role: 'system', content: 'You are a helpful assistant.' },
  { role: 'user', content: 'Hello' },
]

function mockAnthropicResponse(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 'msg_01',
    type: 'message',
    role: 'assistant',
    content: [{ type: 'text', text: 'Hi there!' }],
    model: 'claude-sonnet-4',
    stop_reason: 'end_turn',
    usage: { input_tokens: 10, output_tokens: 5 },
    ...overrides,
  }
}

describe('LLMAdapter Contract', () => {
  it('ClaudeAdapter returns ChatResponse with correct structure', async () => {
    const { ClaudeAdapter } = await import('@agent-platform/llm-adapter')

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockAnthropicResponse(),
    })

    const adapter = new ClaudeAdapter(
      { provider: 'anthropic', apiKey: 'test-key' },
      { fetchFn: mockFetch as unknown as typeof fetch },
    )

    const response: ChatResponse = await adapter.complete(standardMessages)

    expect(response.message).toBeDefined()
    expect(response.message.role).toBe('assistant')
    expect(response.message.content).toBe('Hi there!')
    expect(response.usage).toBeDefined()
    expect(response.usage.promptTokens).toBe(10)
    expect(response.usage.completionTokens).toBe(5)
    expect(response.usage.totalTokens).toBe(15)
    expect(response.finishReason).toBe('stop')
  })

  it('ClaudeAdapter handles tool_calls response', async () => {
    const { ClaudeAdapter } = await import('@agent-platform/llm-adapter')

    const toolResponse = mockAnthropicResponse({
      content: [
        { type: 'text', text: 'Let me check that.' },
        {
          type: 'tool_use',
          id: 'toolu_01',
          name: 'read_file',
          input: { path: '/test/file.txt' },
        },
      ],
      stop_reason: 'tool_use',
    })

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => toolResponse,
    })

    const adapter = new ClaudeAdapter(
      { provider: 'anthropic', apiKey: 'test-key' },
      { fetchFn: mockFetch as unknown as typeof fetch },
    )

    const tools = [
      {
        name: 'read_file',
        description: 'Read a file',
        parameters: {
          type: 'object',
          properties: { path: { type: 'string' } },
          required: ['path'],
        },
      },
    ]

    const response = await adapter.complete(standardMessages, tools)

    expect(response.message.toolCalls).toBeDefined()
    expect(response.message.toolCalls).toHaveLength(1)
    expect(response.message.toolCalls![0].name).toBe('read_file')
    expect(response.message.toolCalls![0].id).toBe('toolu_01')
    expect(response.message.toolCalls![0].arguments).toEqual({
      path: '/test/file.txt',
    })
    expect(response.finishReason).toBe('tool_calls')
  })
})
