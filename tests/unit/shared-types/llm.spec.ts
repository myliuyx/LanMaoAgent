import { describe, it, expect } from 'vitest'
import type { ChatResponse, TokenUsage, AgentResult } from '@agent-platform/shared-types'

describe('TokenUsage', () => {
  it('has required token fields', () => {
    const usage: TokenUsage = { promptTokens: 100, completionTokens: 50, totalTokens: 150 }
    expect(usage.promptTokens).toBe(100)
    expect(usage.completionTokens).toBe(50)
    expect(usage.totalTokens).toBe(150)
  })

  it('totalTokens equals promptTokens + completionTokens by convention', () => {
    const usage: TokenUsage = { promptTokens: 200, completionTokens: 80, totalTokens: 280 }
    expect(usage.totalTokens).toBe(usage.promptTokens + usage.completionTokens)
  })

  it('does not include vendor-specific fields like cacheReadTokens', () => {
    const usage: TokenUsage = { promptTokens: 10, completionTokens: 5, totalTokens: 15 }
    expect(Object.keys(usage)).toEqual(['promptTokens', 'completionTokens', 'totalTokens'])
  })
})

describe('ChatResponse', () => {
  it('has message with assistant role', () => {
    const response: ChatResponse = {
      message: { role: 'assistant', content: 'Hello!' },
      usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
      finishReason: 'stop',
    }
    expect(response.message.role).toBe('assistant')
    expect(response.message.content).toBe('Hello!')
  })

  it('content is optional when toolCalls present', () => {
    const response: ChatResponse = {
      message: {
        role: 'assistant',
        toolCalls: [{ id: 'c1', name: 'read_file', arguments: {} }],
      },
      usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
      finishReason: 'tool_calls',
    }
    expect(response.message.toolCalls).toHaveLength(1)
  })

  it('finishReason is a union of four literal values', () => {
    const stop: ChatResponse['finishReason'] = 'stop'
    const tool: ChatResponse['finishReason'] = 'tool_calls'
    const len: ChatResponse['finishReason'] = 'length'
    const filter: ChatResponse['finishReason'] = 'content_filter'
    expect([stop, tool, len, filter]).toHaveLength(4)
  })
})

describe('AgentResult', () => {
  it('has completed status with output', () => {
    const result: AgentResult = { status: 'completed', output: 'Done', agentId: 'coding-agent' }
    expect(result.status).toBe('completed')
    expect(result.output).toBe('Done')
  })

  it('status is a union of three literal values', () => {
    const completed: AgentResult['status'] = 'completed'
    const maxIter: AgentResult['status'] = 'max_iterations_reached'
    const failed: AgentResult['status'] = 'failed'
    expect([completed, maxIter, failed]).toHaveLength(3)
  })

  it('output and error are optional', () => {
    const result: AgentResult = { status: 'failed', agentId: 'orchestrator' }
    expect(result.output).toBeUndefined()
    expect(result.error).toBeUndefined()
  })

  it('failed status can carry error message', () => {
    const result: AgentResult = {
      status: 'failed',
      agentId: 'orchestrator',
      error: 'LLM API call failed',
    }
    expect(result.error).toContain('LLM')
  })
})
