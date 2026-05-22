import { describe, it, expect, vi } from 'vitest'
import { runAgentLoop } from '@agent-platform/tool-core'
import { ShortTermMemory } from '@agent-platform/memory-stm'
import type {
  Agent,
  ChatMessage,
  ChatResponse,
  ToolDefinition,
  ToolCall,
} from '@agent-platform/shared-types'
import type { ToolRegistry } from '@agent-platform/tool-core'

function mockLLM(responses: ChatResponse[]) {
  let i = 0
  return {
    complete: vi.fn().mockImplementation(async () => responses[i++] ?? {
      message: { role: 'assistant', content: 'done' },
      usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
      finishReason: 'stop',
    }),
  }
}

function mockRegistry(toolResults: string[] = ['tool output']) {
  let i = 0
  return {
    getAllTools: () => [] as ToolDefinition[],
    execute: vi.fn().mockImplementation(async (_call: ToolCall) => ({
      content: toolResults[i++ % toolResults.length] ?? 'result',
      isError: false,
    })),
  } as unknown as ToolRegistry
}

const agent: Agent = {
  id: 'test-agent',
  name: 'Test',
  description: 'A test agent',
  systemPrompt: 'You are a test agent.',
  model: 'test-model',
  tools: [],
}

function msg(role: ChatMessage['role'], content: string): ChatMessage {
  return { role, content }
}

describe('runAgentLoop', () => {
  it('LLM returns only text → immediate completion', async () => {
    const llm = mockLLM([
      {
        message: { role: 'assistant', content: 'Hello!' },
        usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
        finishReason: 'stop',
      },
    ])
    const result = await runAgentLoop({
      agent,
      messages: [msg('user', 'Hi')],
      llm,
      registry: mockRegistry(),
      ctx: { sessionId: 's1', agentId: 'a1', cwd: '/tmp' },
    })
    expect(result.status).toBe('completed')
    expect(result.output).toBe('Hello!')
    expect(llm.complete).toHaveBeenCalledTimes(1)
  })

  it('LLM returns tool_calls → execute tools via registry → continue loop', async () => {
    const llm = mockLLM([
      {
        message: {
          role: 'assistant',
          content: 'Let me check...',
          toolCalls: [{ id: 'tc1', name: 'read_file', arguments: { path: '/f' } }],
        },
        usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
        finishReason: 'tool_calls',
      },
      {
        message: { role: 'assistant', content: 'Done!' },
        usage: { promptTokens: 20, completionTokens: 10, totalTokens: 30 },
        finishReason: 'stop',
      },
    ])
    const registry = mockRegistry(['file content'])
    const result = await runAgentLoop({
      agent,
      messages: [msg('user', 'Read file')],
      llm,
      registry,
      ctx: { sessionId: 's1', agentId: 'a1', cwd: '/tmp' },
    })
    expect(result.status).toBe('completed')
    expect(result.output).toBe('Done!')
    expect(llm.complete).toHaveBeenCalledTimes(2)
    expect(registry.execute).toHaveBeenCalledTimes(1)
    expect(registry.execute).toHaveBeenCalledWith(
      { id: 'tc1', name: 'read_file', arguments: { path: '/f' } },
      expect.objectContaining({ sessionId: 's1' }),
    )
  })

  it('exceeds maxIterations → max_iterations_reached', async () => {
    const toolResponse: ChatResponse = {
      message: {
        role: 'assistant',
        content: 'thinking...',
        toolCalls: [{ id: 'tc1', name: 'read_file', arguments: { path: '/f' } }],
      },
      usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
      finishReason: 'tool_calls',
    }
    const llm = mockLLM(Array(10).fill(toolResponse))
    const registry = mockRegistry(['result'])
    const result = await runAgentLoop({
      agent,
      messages: [msg('user', 'Hi')],
      llm,
      registry,
      ctx: { sessionId: 's1', agentId: 'a1', cwd: '/tmp' },
      maxIterations: 3,
    })
    expect(result.status).toBe('max_iterations_reached')
    expect(llm.complete).toHaveBeenCalledTimes(3)
    expect(registry.execute).toHaveBeenCalledTimes(3)
  })

  it('signal.aborted → aborted', async () => {
    const controller = new AbortController()
    controller.abort()
    const llm = mockLLM([])
    const result = await runAgentLoop({
      agent,
      messages: [msg('user', 'Hi')],
      llm,
      registry: mockRegistry(),
      ctx: { sessionId: 's1', agentId: 'a1', cwd: '/tmp' },
      signal: controller.signal,
    })
    expect(result.status).toBe('aborted')
    expect(llm.complete).not.toHaveBeenCalled()
  })

  it('calls onToolStart/onToolFinish when tool calls are made', async () => {
    const llm = mockLLM([
      {
        message: {
          role: 'assistant',
          content: 'checking...',
          toolCalls: [{ id: 'tc1', name: 'read_file', arguments: { path: '/f' } }],
        },
        usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
        finishReason: 'tool_calls',
      },
      {
        message: { role: 'assistant', content: 'Done' },
        usage: { promptTokens: 20, completionTokens: 10, totalTokens: 30 },
        finishReason: 'stop',
      },
    ])
    const registry = mockRegistry(['content'])
    const onToolStart = vi.fn()
    const onToolFinish = vi.fn()

    await runAgentLoop({
      agent,
      messages: [msg('user', 'read')],
      llm,
      registry,
      ctx: { sessionId: 's1', agentId: 'a1', cwd: '/tmp' },
      onToolStart,
      onToolFinish,
    })

    expect(onToolStart).toHaveBeenCalledTimes(1)
    expect(onToolStart).toHaveBeenCalledWith({ id: 'tc1', name: 'read_file', arguments: { path: '/f' } }, 'test-agent')
    expect(onToolFinish).toHaveBeenCalledWith(
      { id: 'tc1', name: 'read_file', arguments: { path: '/f' } },
      { content: 'content', isError: false },
      'test-agent',
    )
  })

  describe('token budget + STM compact', () => {
    const toolResponse: ChatResponse = {
      message: {
        role: 'assistant',
        content: 'thinking...',
        toolCalls: [{ id: 'tc1', name: 'read_file', arguments: { path: '/f' } }],
      },
      usage: { promptTokens: 50, completionTokens: 30, totalTokens: 80 },
      finishReason: 'tool_calls',
    }

    it('compact triggers when context size exceeds budget', async () => {
      // budget = 100 * 0.5 = 50; 30 messages of 'padding' ≈ 60 tokens > 50
      const stm = new ShortTermMemory()
      for (let i = 0; i < 60; i++) {
        stm.add({ role: 'user', content: 'padding' })
      }
      const compactSpy = vi.spyOn(stm, 'compact')
      const largeMessages = Array.from({ length: 30 }, () => msg('user', 'padding'))

      const llm = mockLLM([
        toolResponse,
        {
          message: { role: 'assistant', content: 'done' },
          usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
          finishReason: 'stop',
        },
      ])
      await runAgentLoop({
        agent,
        messages: largeMessages,
        llm,
        registry: mockRegistry(['result']),
        ctx: { sessionId: 's1', agentId: 'a1', cwd: '/tmp' },
        memory: stm,
        contextWindow: 100,
        compressionRatio: 0.5,
        maxIterations: 10,
      })
      expect(compactSpy).toHaveBeenCalledTimes(1)
    })

    it('compact returns 0 is not a failure', async () => {
      const stm = new ShortTermMemory()
      const compactSpy = vi.spyOn(stm, 'compact')

      // budget = 50; 30 padding messages ≈ 60 tokens → triggers compact
      // But STM is empty (0 ≤ threshold 50) → compact returns 0
      const largeMessages = Array.from({ length: 30 }, () => msg('user', 'padding'))
      const oneToolCall = [toolResponse]
      const llm = mockLLM(oneToolCall)

      const result = await runAgentLoop({
        agent,
        messages: largeMessages,
        llm,
        registry: mockRegistry(['result']),
        ctx: { sessionId: 's1', agentId: 'a1', cwd: '/tmp' },
        memory: stm,
        contextWindow: 100,
        compressionRatio: 0.5,
        maxIterations: 10,
      })

      // compact() returns 0 when messages.length <= threshold — not a failure
      expect(result.status).toBe('completed')
      expect(compactSpy).toHaveBeenCalled()
    })

    it('compact syncs back to local messages array', async () => {
      const stm = new ShortTermMemory()
      // 填满 STM 使其可压缩
      for (let i = 0; i < 60; i++) {
        stm.add({ role: 'user', content: 'padding '.repeat(20) })
      }

      // 初始消息足够大，使 llmTokenEstimate > budget (100)
      const largeMessages = Array.from({ length: 30 }, () => msg('user', 'padding '.repeat(20)))
      // 把 STM 也同步为大消息，确保 compact 能跑
      for (const m of largeMessages) {
        stm.add(m)
      }

      const toolResponseLocal: ChatResponse = {
        message: {
          role: 'assistant',
          content: 'thinking...',
          toolCalls: [{ id: 'tc1', name: 'read_file', arguments: { path: '/f' } }],
        },
        usage: { promptTokens: 100, completionTokens: 50, totalTokens: 150 },
        finishReason: 'tool_calls',
      }

      const llm = mockLLM([
        toolResponseLocal,
        {
          message: { role: 'assistant', content: 'done' },
          usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
          finishReason: 'stop',
        },
      ])

      // budget = 200 * 0.5 = 100，30 条大消息 ≈ 2400 tokens > 100 → 触发 compact
      await runAgentLoop({
        agent,
        messages: largeMessages,
        llm,
        registry: mockRegistry(['result']),
        ctx: { sessionId: 's1', agentId: 'a1', cwd: '/tmp' },
        memory: stm,
        contextWindow: 200,
        compressionRatio: 0.5,
        maxIterations: 10,
      })

      // 验证：第二次迭代时 LLM 收到的消息中包含压缩摘要
      const secondCallArgs = llm.complete.mock.calls[1][0] as ChatMessage[]
      const hasSummary = secondCallArgs.some(
        (m) => m.role === 'system' && m.content.includes('[User Messages]'),
      )
      expect(hasSummary).toBe(true)
    })
  })
})
