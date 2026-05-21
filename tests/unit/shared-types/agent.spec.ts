import { describe, it, expect } from 'vitest'
import type { Agent, ToolHandler, ToolExecutionContext } from '@agent-platform/shared-types'
import type { ToolCall, ToolResult } from '@agent-platform/shared-types'

describe('ToolHandler', () => {
  it('interface has id, getTools, and execute methods', () => {
    const handler: ToolHandler = {
      id: 'test-handler',
      getTools: () => [],
      execute: async (_call: ToolCall, _ctx: ToolExecutionContext) => {
        return { content: 'ok', isError: false } as ToolResult
      },
    }
    expect(handler.id).toBe('test-handler')
    expect(handler.getTools()).toEqual([])
  })

  it('getTools returns ToolDefinition array', () => {
    const handler: ToolHandler = {
      id: 'reader',
      getTools: () => [
        { name: 'read', description: 'read a file', parameters: { type: 'object' } },
      ],
      execute: async () => ({ content: '', isError: false }),
    }
    const tools = handler.getTools()
    expect(tools).toHaveLength(1)
    expect(tools[0].name).toBe('read')
  })

  it('execute returns Promise<ToolResult>', async () => {
    const handler: ToolHandler = {
      id: 'pinger',
      getTools: () => [],
      execute: async () => ({ content: 'pong', isError: false }),
    }
    const call: ToolCall = { id: 'c1', name: 'ping', arguments: {} }
    const ctx: ToolExecutionContext = { sessionId: 's1', agentId: 'a1', cwd: '/tmp' }
    const result = await handler.execute(call, ctx)
    expect(result.content).toBe('pong')
    expect(result.isError).toBe(false)
  })
})

describe('ToolExecutionContext', () => {
  it('has required sessionId, agentId, cwd fields', () => {
    const ctx: ToolExecutionContext = {
      sessionId: 'session_1',
      agentId: 'coding-agent',
      cwd: '/home/project',
    }
    expect(ctx.sessionId).toBe('session_1')
    expect(ctx.agentId).toBe('coding-agent')
    expect(ctx.cwd).toBe('/home/project')
  })

  it('allowedPaths is optional', () => {
    const ctx: ToolExecutionContext = {
      sessionId: 's1',
      agentId: 'a1',
      cwd: '/tmp',
    }
    expect(ctx.allowedPaths).toBeUndefined()
  })

  it('allowedPaths can be set when needed', () => {
    const ctx: ToolExecutionContext = {
      sessionId: 's1',
      agentId: 'a1',
      cwd: '/tmp',
      allowedPaths: ['/tmp', '/home/project'],
    }
    expect(ctx.allowedPaths).toHaveLength(2)
  })
})

describe('Agent', () => {
  it('has readonly id and name', () => {
    const agent: Agent = {
      id: 'coding-agent',
      name: '编码专家',
      description: 'Writes code',
      systemPrompt: 'You are a developer.',
      model: 'claude-sonnet-4',
      tools: [],
    }
    expect(agent.id).toBe('coding-agent')
    expect(agent.name).toBe('编码专家')
  })

  it('has optional temperature and maxTokens', () => {
    const agent: Agent = {
      id: 'test',
      name: 'Test',
      description: '',
      systemPrompt: '',
      model: 'claude-sonnet-4',
      temperature: 0.5,
      maxTokens: 4096,
      tools: [],
    }
    expect(agent.temperature).toBe(0.5)
    expect(agent.maxTokens).toBe(4096)
  })

  it('has optional contextWindow', () => {
    const agent: Agent = {
      id: 'test',
      name: 'Test',
      description: '',
      systemPrompt: '',
      model: 'claude-sonnet-4',
      contextWindow: 200000,
      tools: [],
    }
    expect(agent.contextWindow).toBe(200000)
  })
})
