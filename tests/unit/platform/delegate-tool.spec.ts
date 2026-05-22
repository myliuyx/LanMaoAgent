import { describe, it, expect, vi, beforeEach } from 'vitest'
import type {
  Agent,
  ToolCall,
  ToolExecutionContext,
} from '@agent-platform/shared-types'

vi.mock('@agent-platform/tool-core', () => ({
  runAgentLoop: vi.fn().mockResolvedValue({
    status: 'completed',
    output: 'refactored the code',
    agentId: 'coding-agent',
  }),
}))

describe('DelegateToAgentHandler', () => {
  beforeEach(() => {
    vi.resetModules()
  })
  it('delegates to known coding-agent and returns JSON with output', async () => {
    const { DelegateToAgentHandler } = await import('@agent-platform/platform')
    const { runAgentLoop } = await import('@agent-platform/tool-core')

    const codingAgent: Agent = {
      id: 'coding-agent',
      name: 'Coding Agent',
      description: 'Coding expert',
      systemPrompt: 'You are a coding expert',
      model: 'claude-sonnet-4',
      tools: [],
    }

    const resolver = { get: vi.fn().mockReturnValue(codingAgent) }
    const llm = { complete: vi.fn() }
    const registry = {
      register: vi.fn(),
      getAllTools: vi.fn().mockReturnValue([]),
      execute: vi.fn(),
    }

    const handler = new DelegateToAgentHandler(resolver, llm, registry)
    expect(handler.id).toBe('delegate_to_agent')

    const tools = handler.getTools()
    expect(tools).toHaveLength(1)
    expect(tools[0].name).toBe('delegate_to_agent')
    expect(tools[0].parameters).toEqual({
      type: 'object',
      properties: {
        agentId: { type: 'string', description: 'The agent to delegate to' },
        task: {
          type: 'string',
          description: 'The task description to delegate',
        },
        context: {
          type: 'string',
          description:
            'Optional conversation context from parent (e.g., prior tool results)',
        },
      },
      required: ['agentId', 'task'],
    })

    const call: ToolCall = {
      id: 'call-1',
      name: 'delegate_to_agent',
      arguments: { agentId: 'coding-agent', task: 'Refactor the main module' },
    }

    const ctx: ToolExecutionContext = {
      sessionId: 'session-1',
      agentId: 'orchestrator',
      cwd: '/project',
    }

    const result = await handler.execute(call, ctx)

    expect(resolver.get).toHaveBeenCalledWith('coding-agent')
    expect(runAgentLoop).toHaveBeenCalled()
    const loopArgs = (runAgentLoop as ReturnType<typeof vi.fn>).mock.calls[0][0]
    expect(loopArgs.agent).toBe(codingAgent)
    expect(loopArgs.messages).toHaveLength(2)
    expect(loopArgs.messages[0].role).toBe('system')
    expect(loopArgs.messages[0].content).toBe('You are a coding expert')
    expect(loopArgs.messages[1].role).toBe('user')
    expect(loopArgs.messages[1].content).toBe('Refactor the main module')
    expect(loopArgs.ctx.sessionId).not.toBe('session-1')
    expect(loopArgs.ctx.sessionId).toMatch(/^sub-/)
    expect(loopArgs.memory).toBeDefined()
    expect(loopArgs.registry).toBe(registry)
    expect(loopArgs.llm).toBe(llm)

    expect(result.isError).toBeFalsy()
    expect(result.content).toBe('refactored the code')
    expect(result.metadata).toEqual({ agentId: 'coding-agent' })
  })

  it('returns isError when sub-agent is aborted', async () => {
    const { runAgentLoop } = await import('@agent-platform/tool-core')
    ;(runAgentLoop as ReturnType<typeof vi.fn>).mockResolvedValue({
      status: 'aborted',
      agentId: 'coding-agent',
    })

    const { DelegateToAgentHandler } = await import('@agent-platform/platform')

    const codingAgent: Agent = {
      id: 'coding-agent',
      name: 'CA',
      description: '',
      systemPrompt: '',
      model: 'claude-sonnet-4',
      tools: [],
    }

    const resolver = { get: vi.fn().mockReturnValue(codingAgent) }
    const llm = { complete: vi.fn() }
    const registry = {
      register: vi.fn(),
      getAllTools: vi.fn().mockReturnValue([]),
      execute: vi.fn(),
    }

    const handler = new DelegateToAgentHandler(resolver, llm, registry)

    const call: ToolCall = {
      id: 'c1',
      name: 'delegate_to_agent',
      arguments: { agentId: 'coding-agent', task: 'do' },
    }

    const ctx: ToolExecutionContext = {
      sessionId: 's1',
      agentId: 'orchestrator',
      cwd: '/p',
    }

    const result = await handler.execute(call, ctx)

    expect(result.isError).toBe(true)
    expect(result.content).toContain('aborted')
  })

  it('returns isError for unknown agent', async () => {
    const { DelegateToAgentHandler } = await import('@agent-platform/platform')

    const resolver = { get: vi.fn().mockReturnValue(undefined) }
    const llm = { complete: vi.fn() }
    const registry = {
      register: vi.fn(),
      getAllTools: vi.fn().mockReturnValue([]),
      execute: vi.fn(),
    }

    const handler = new DelegateToAgentHandler(resolver, llm, registry)

    const call: ToolCall = {
      id: 'call-2',
      name: 'delegate_to_agent',
      arguments: { agentId: 'nonexistent', task: 'do something' },
    }

    const ctx: ToolExecutionContext = {
      sessionId: 'session-1',
      agentId: 'orchestrator',
      cwd: '/project',
    }

    const result = await handler.execute(call, ctx)

    expect(result.isError).toBe(true)
    expect(result.content).toBe('Unknown agent')
    expect(resolver.get).toHaveBeenCalledWith('nonexistent')
  })
})
