import { describe, it, expect, vi, beforeEach } from 'vitest'

const runAgentLoopMock = vi.fn().mockResolvedValue({
  status: 'completed',
  output: 'done',
  agentId: 'orchestrator',
})

vi.mock('@agent-platform/llm-adapter', () => {
  const mockComplete = vi.fn()
  return {
    ClaudeAdapter: vi.fn(function MockClaude() {
      return { complete: mockComplete }
    }),
  }
})

vi.mock('@agent-platform/tool-core', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@agent-platform/tool-core')>()
  return {
    ...actual,
    runAgentLoop: runAgentLoopMock,
  }
})

vi.mock('@agent-platform/tools-terminal', () => {
  let capturedWhitelist: string[] | undefined = undefined
  const mockExecute = vi.fn().mockResolvedValue({
    content: '',
    isError: false,
  })
  return {
    TerminalHandler: vi.fn(function MockTerminal(whitelist?: string[]) {
      capturedWhitelist = whitelist
      return {
        id: 'terminal',
        getTools: () => [
          {
            name: 'exec_command',
            description: 'Execute a shell command',
            parameters: {
              type: 'object',
              properties: { command: { type: 'string' } },
              required: ['command'],
            },
          },
        ],
        execute: mockExecute,
      }
    }),
    __getCapturedWhitelist: () => capturedWhitelist,
  }
})

describe('Platform', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('constructor throws when apiKey is empty or missing', async () => {
    const { Platform } = await import('@agent-platform/platform')

    expect(
      () =>
        new Platform({
          llm: { provider: 'anthropic', apiKey: '' },
          agents: [],
        }),
    ).toThrow('llm.apiKey required')

    expect(
      () =>
        new Platform({
          llm: { provider: 'anthropic', apiKey: '' },
          agents: [],
        }),
    ).toThrow('llm.apiKey required')
  })

  it('createSession returns Session with independent STM instances', async () => {
    const { Platform } = await import('@agent-platform/platform')

    const platform = new Platform({
      llm: { provider: 'anthropic', apiKey: 'test-key' },
      agents: [
        {
          id: 'orchestrator',
          name: 'Orchestrator',
          description: 'Orchestrator agent',
          systemPrompt: 'You are an orchestrator',
          tools: ['delegate_to_agent'],
        },
      ],
    })

    const s1 = platform.createSession('orchestrator', '/project/a')
    const s2 = platform.createSession('coding-agent', '/project/b')

    expect(s1.id).toBeTruthy()
    expect(s2.id).toBeTruthy()
    expect(s1.id).not.toBe(s2.id)
    expect(s1.agentId).toBe('orchestrator')
    expect(s2.agentId).toBe('coding-agent')
    expect(s1.projectRoot).toBe('/project/a')
    expect(s2.projectRoot).toBe('/project/b')
    expect(s1.stm).not.toBe(s2.stm)
  })

  it('TerminalHandler uses custom whitelist from config', async () => {
    const { Platform } = await import('@agent-platform/platform')
    const mockModule = await import('@agent-platform/tools-terminal')
    const getWhitelist = (
      mockModule as unknown as {
        __getCapturedWhitelist: () => string[] | undefined
      }
    ).__getCapturedWhitelist

    const customWhitelist = ['ls', 'echo']

    new Platform({
      llm: { provider: 'anthropic', apiKey: 'test-key' },
      agents: [
        {
          id: 'orchestrator',
          name: 'Orchestrator',
          description: 'Orchestrator agent',
          systemPrompt: 'You are an orchestrator',
          tools: ['delegate_to_agent'],
        },
      ],
      security: { terminalWhitelist: customWhitelist, allowedPaths: [] },
    })

    expect(getWhitelist()).toEqual(customWhitelist)
  })

  it('run() with pre-aborted signal returns aborted result immediately', async () => {
    const { Platform } = await import('@agent-platform/platform')

    const platform = new Platform({
      llm: { provider: 'anthropic', apiKey: 'test-key' },
      agents: [
        {
          id: 'orchestrator',
          name: 'Orchestrator',
          description: 'Orchestrator agent',
          systemPrompt: 'You are an orchestrator',
          tools: ['delegate_to_agent'],
        },
      ],
    })

    const ac = new AbortController()
    ac.abort()

    const result = await platform.run('hello', ac.signal)

    expect(result.status).toBe('aborted')
    expect(result.agentId).toBe('orchestrator')
  })

  it('run() returns failed when runAgentLoop throws', async () => {
    runAgentLoopMock.mockRejectedValueOnce(new Error('LLM unavailable'))
    const { Platform } = await import('@agent-platform/platform')

    const platform = new Platform({
      llm: { provider: 'anthropic', apiKey: 'test-key' },
      agents: [
        {
          id: 'orchestrator',
          name: 'Orchestrator',
          description: 'Orchestrator agent',
          systemPrompt: 'You are an orchestrator',
          tools: ['delegate_to_agent'],
        },
      ],
    })

    const result = await platform.run('hello')

    expect(result.status).toBe('failed')
    expect(result.agentId).toBe('orchestrator')
    expect(result.error).toBe('LLM unavailable')
  })
})
