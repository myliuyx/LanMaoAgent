import { describe, it, expect } from 'vitest'

describe('Agents config', () => {
  it('BUILTIN_AGENTS contains orchestrator and coding-agent as pure data', async () => {
    const { BUILTIN_AGENTS } = await import('@agent-platform/platform')

    expect(BUILTIN_AGENTS).toHaveLength(5)
    expect(BUILTIN_AGENTS[0].id).toBe('orchestrator')
    expect(BUILTIN_AGENTS[1].id).toBe('coding-agent')
    expect(BUILTIN_AGENTS[2].id).toBe('planner')
    expect(BUILTIN_AGENTS[3].id).toBe('reviewer')
    expect(BUILTIN_AGENTS[4].id).toBe('tester')

    expect(BUILTIN_AGENTS[0].tools).toEqual(['delegate_to_agent'])
    expect(BUILTIN_AGENTS[1].tools).toEqual(['filesystem', 'git', 'terminal'])
    expect(BUILTIN_AGENTS[2].tools).toEqual(['filesystem'])
    expect(BUILTIN_AGENTS[3].tools).toEqual(['filesystem', 'git', 'terminal'])
    expect(BUILTIN_AGENTS[4].tools).toEqual(['filesystem', 'git', 'terminal'])

    for (const agent of BUILTIN_AGENTS) {
      expect(agent).not.toHaveProperty('model')
      expect(agent).not.toHaveProperty('temperature')
      expect('systemPrompt' in agent).toBe(true)
    }
  })

  it('buildAgent returns complete Agent with merged params', async () => {
    const { BUILTIN_AGENTS, buildAgent } = await import(
      '@agent-platform/platform'
    )
    const mockHandler = { id: 'mock', getTools: () => [], execute: async () => ({ content: '', isError: false }) }

    const agent = buildAgent(
      BUILTIN_AGENTS[0],
      [mockHandler],
      { model: 'custom-model', temperature: 0.5 },
    )

    expect(agent.id).toBe('orchestrator')
    expect(agent.name).toBe('编排者')
    expect(agent.model).toBe('custom-model')
    expect(agent.temperature).toBe(0.5)
    expect(agent.description).toBeTruthy()
    expect(agent.systemPrompt).toBeTruthy()
    expect(agent.tools).toHaveLength(1)
    expect(agent.tools[0]).toBe(mockHandler)
  })

  it('buildAgent uses DEFAULT_AGENT_PARAMS when no params given', async () => {
    const { BUILTIN_AGENTS, buildAgent, DEFAULT_AGENT_PARAMS } = await import(
      '@agent-platform/platform'
    )

    const agent = buildAgent(BUILTIN_AGENTS[0], [])

    expect(agent.model).toBe(DEFAULT_AGENT_PARAMS.model)
    expect(agent.temperature).toBe(DEFAULT_AGENT_PARAMS.temperature)
    expect(agent.maxTokens).toBe(DEFAULT_AGENT_PARAMS.maxTokens)
    expect(agent.contextWindow).toBe(DEFAULT_AGENT_PARAMS.contextWindow)
  })

  it('buildAgent returns agent with no handler reference mutation', async () => {
    const { BUILTIN_AGENTS, buildAgent } = await import(
      '@agent-platform/platform'
    )

    const agent = buildAgent(BUILTIN_AGENTS[0], [])

    expect(agent.tools).toEqual([])
  })
})
