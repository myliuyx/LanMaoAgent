import { describe, it, expect, vi, beforeEach } from 'vitest'

const exitMock = vi.fn<[number], void>()
const logMock = vi.fn()
const errorMock = vi.fn()
const runMock = vi.fn()
const platformCtorMock = vi.fn()
const onMock = vi.fn()

describe('CLI Agent Loading', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    exitMock.mockClear()
    logMock.mockClear()
    errorMock.mockClear()
    runMock.mockReset()
    platformCtorMock.mockClear()
    onMock.mockClear()
  })

  it('loads agents from filesystem when agentsDir exists with index.json', async () => {
    const { runCli } = await import('../../../apps/cli/src/index.ts')

    const calls: string[] = []
    const mockReadFileSync = vi.fn().mockImplementation((path: string) => {
      calls.push(path)
      if (path.endsWith('config.json')) {
        return JSON.stringify({ llm: { apiKey: 'test-key' } })
      }
      if (path.endsWith('index.json')) {
        return JSON.stringify(['orchestrator', 'coding-agent'])
      }
      if (path.endsWith('orchestrator/agent.json')) {
        return JSON.stringify({
          name: '编排者',
          description: '编排者',
          tools: ['delegate_to_agent'],
        })
      }
      if (path.endsWith('orchestrator/system-prompt.md')) {
        return '你是编排者'
      }
      if (path.endsWith('coding-agent/agent.json')) {
        return JSON.stringify({
          name: '编码专家',
          description: '编码专家',
          tools: ['filesystem', 'git'],
        })
      }
      if (path.endsWith('coding-agent/system-prompt.md')) {
        return '你是编码专家'
      }
      throw new Error(`ENOENT: ${path}`)
    })

    runCli({
      readFileSync:
        mockReadFileSync as unknown as typeof import('fs').readFileSyncSync,
      process: {
        env: { ANTHROPIC_API_KEY: 'test-key' },
        exit: exitMock,
        on: onMock,
        stdout: { write: vi.fn(), isTTY: true },
        stdin: { on: vi.fn(), setRawMode: vi.fn() },
        argv: ['node', 'test'],
      } as unknown as NodeJS.Process,
      console: { log: logMock, error: errorMock } as unknown as Console,
      PlatformCtor:
        platformCtorMock.mockImplementation(function MockPlatform() {
          return { run: runMock }
        }),
      readline: {
        createInterface: vi.fn().mockReturnValue({
          on: vi.fn(),
          close: vi.fn(),
          prompt: vi.fn(),
          write: vi.fn(),
        }),
      } as unknown as typeof import('node:readline'),
    })

    expect(platformCtorMock).toHaveBeenCalled()
    const config = platformCtorMock.mock.calls[0][0]

    expect(config.agents).toHaveLength(2)

    const orchestrator = config.agents.find(
      (a: { id: string }) => a.id === 'orchestrator',
    )
    expect(orchestrator).toBeDefined()
    expect(orchestrator.name).toBe('编排者')
    expect(orchestrator.systemPrompt).toBe('你是编排者')
    expect(orchestrator.tools).toContain('delegate_to_agent')
    // agent with explicit tools should NOT get defaultTools merged
    expect(orchestrator.tools).not.toContain('filesystem')
    expect(orchestrator.tools).not.toContain('git')
    expect(orchestrator.tools).not.toContain('terminal')
    expect(orchestrator.tools).toHaveLength(1)

    const coding = config.agents.find(
      (a: { id: string }) => a.id === 'coding-agent',
    )
    expect(coding).toBeDefined()
    expect(coding.systemPrompt).toBe('你是编码专家')
    expect(coding.tools).toContain('filesystem')
    expect(coding.tools).toContain('git')
    expect(coding.tools).not.toContain('terminal')
    expect(coding.tools).toHaveLength(2)
  })

  it('falls back to built-in agents when agentsDir is missing', async () => {
    const { runCli } = await import('../../../apps/cli/src/index.ts')

    const mockReadFileSync = vi.fn().mockImplementation(() => {
      throw new Error('ENOENT')
    })

    runCli({
      readFileSync:
        mockReadFileSync as unknown as typeof import('fs').readFileSyncSync,
      process: {
        env: { ANTHROPIC_API_KEY: 'test-key' },
        exit: exitMock,
        on: onMock,
        stdout: { write: vi.fn(), isTTY: true },
        stdin: { on: vi.fn(), setRawMode: vi.fn() },
        argv: ['node', 'test'],
      } as unknown as NodeJS.Process,
      console: { log: logMock, error: errorMock } as unknown as Console,
      PlatformCtor:
        platformCtorMock.mockImplementation(function MockPlatform() {
          return { run: runMock }
        }),
      readline: {
        createInterface: vi.fn().mockReturnValue({
          on: vi.fn(),
          close: vi.fn(),
          prompt: vi.fn(),
          write: vi.fn(),
        }),
      } as unknown as typeof import('node:readline'),
    })

    expect(platformCtorMock).toHaveBeenCalled()
    const config = platformCtorMock.mock.calls[0][0]

    // Should fall back to BUILTIN_AGENTS
    expect(config.agents.length).toBeGreaterThanOrEqual(2)
    expect(config.agents.find((a: { id: string }) => a.id === 'orchestrator')).toBeDefined()
    expect(config.agents.find((a: { id: string }) => a.id === 'coding-agent')).toBeDefined()
  })

  it('falls back to built-in agent when specific agent dir is missing', async () => {
    const { runCli } = await import('../../../apps/cli/src/index.ts')

    const calls: string[] = []
    const mockReadFileSync = vi.fn().mockImplementation((path: string) => {
      calls.push(path)
      if (path.endsWith('config.json')) {
        return JSON.stringify({ llm: { apiKey: 'test-key' } })
      }
      if (path.endsWith('index.json')) {
        return JSON.stringify(['orchestrator', 'coding-agent'])
      }
      if (path.endsWith('orchestrator/agent.json')) {
        return JSON.stringify({
          name: '编排者',
          description: '编排者',
          tools: ['delegate_to_agent'],
        })
      }
      if (path.endsWith('orchestrator/system-prompt.md')) {
        return '你是编排者'
      }
      // coding-agent directory doesn't exist — will fall back to built-in
      throw new Error(`ENOENT: ${path}`)
    })

    runCli({
      readFileSync:
        mockReadFileSync as unknown as typeof import('fs').readFileSyncSync,
      process: {
        env: { ANTHROPIC_API_KEY: 'test-key' },
        exit: exitMock,
        on: onMock,
        stdout: { write: vi.fn(), isTTY: true },
        stdin: { on: vi.fn(), setRawMode: vi.fn() },
        argv: ['node', 'test'],
      } as unknown as NodeJS.Process,
      console: { log: logMock, error: errorMock } as unknown as Console,
      PlatformCtor:
        platformCtorMock.mockImplementation(function MockPlatform() {
          return { run: runMock }
        }),
      readline: {
        createInterface: vi.fn().mockReturnValue({
          on: vi.fn(),
          close: vi.fn(),
          prompt: vi.fn(),
          write: vi.fn(),
        }),
      } as unknown as typeof import('node:readline'),
    })

    expect(platformCtorMock).toHaveBeenCalled()
    const config = platformCtorMock.mock.calls[0][0]

    const coding = config.agents.find(
      (a: { id: string }) => a.id === 'coding-agent',
    )
    expect(coding).toBeDefined()
    // Should have built-in tools (the default ones)
    expect(coding.tools).toContain('filesystem')
  })

  it('throws on circular extends', async () => {
    const { runCli } = await import('../../../apps/cli/src/index.ts')

    const mockReadFileSync = vi.fn().mockImplementation((path: string) => {
      if (path.endsWith('config.json')) {
        return JSON.stringify({ llm: { apiKey: 'test-key' } })
      }
      if (path.endsWith('index.json')) {
        return JSON.stringify(['agent-a'])
      }
      if (path.endsWith('agent-a/agent.json')) {
        return JSON.stringify({
          name: 'Agent A',
          tools: [],
          extends: 'agent-b',
        })
      }
      if (path.endsWith('agent-b/agent.json')) {
        return JSON.stringify({
          name: 'Agent B',
          tools: [],
          extends: 'agent-a',
        })
      }
      throw new Error(`ENOENT: ${path}`)
    })

    expect(() =>
      runCli({
        readFileSync:
          mockReadFileSync as unknown as typeof import('fs').readFileSyncSync,
        process: {
          env: { ANTHROPIC_API_KEY: 'test-key' },
          exit: exitMock,
          on: onMock,
          stdout: { write: vi.fn(), isTTY: true },
          stdin: { on: vi.fn(), setRawMode: vi.fn() },
          argv: ['node', 'test'],
        } as unknown as NodeJS.Process,
        console: { log: logMock, error: errorMock } as unknown as Console,
        readline: {
          createInterface: vi.fn().mockReturnValue({
            on: vi.fn(),
            close: vi.fn(),
            prompt: vi.fn(),
            write: vi.fn(),
          }),
        } as unknown as typeof import('node:readline'),
      }),
    ).toThrow('Circular extends detected')
  })
})
