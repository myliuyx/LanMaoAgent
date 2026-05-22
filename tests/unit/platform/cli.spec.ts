import { describe, it, expect, vi, beforeEach } from 'vitest'

const exitMock = vi.fn<[number], void>()
const logMock = vi.fn()
const errorMock = vi.fn()
const runMock = vi.fn()
const platformCtorMock = vi.fn()
const onMock = vi.fn()

describe('CLI Entry', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    exitMock.mockClear()
    logMock.mockClear()
    errorMock.mockClear()
    runMock.mockReset()
    platformCtorMock.mockClear()
    onMock.mockClear()
  })

  it('missing API_KEY throws from Platform constructor', async () => {
    const { runCli } = await import('../../../apps/cli/src/index.ts')

    expect(() =>
      runCli({
        readFileSync: vi.fn().mockImplementation(() => {
          throw new Error('ENOENT')
        }) as unknown as typeof import('fs').readFileSyncSync,
        process: {
          env: {},
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
    ).toThrow('llm.apiKey required for anthropic provider')
  })

  it('config.json apiKey takes precedence over env var', async () => {
    const { runCli } = await import('../../../apps/cli/src/index.ts')

    const mockReadFileSync = vi.fn().mockReturnValue(
      JSON.stringify({ llm: { apiKey: 'config-key' } }),
    )

    runCli({
      readFileSync:
        mockReadFileSync as unknown as typeof import('fs').readFileSyncSync,
      process: {
        env: { ANTHROPIC_API_KEY: 'env-key' },
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
    expect(config.llm.apiKey).toBe('config-key')
  })

  it('SIGINT prints Exiting... and no error for aborted', async () => {
    const { runCli } = await import('../../../apps/cli/src/index.ts')

    let sigintHandler: () => void = () => {}
    const localOnMock = vi.fn(
      (_event: string, handler: () => void) => {
        if (_event === 'SIGINT') sigintHandler = handler
      },
    )

    const { abortController } = runCli({
      readFileSync: vi.fn().mockImplementation(() => {
        throw new Error('ENOENT')
      }) as unknown as typeof import('fs').readFileSyncSync,
      process: {
        env: { ANTHROPIC_API_KEY: 'test-key' },
        exit: exitMock,
        on: localOnMock,
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

    expect(localOnMock).toHaveBeenCalledWith('SIGINT', expect.any(Function))

    sigintHandler()

    expect(logMock).toHaveBeenCalledWith('\nExiting...')
    expect(abortController.signal.aborted).toBe(true)
  })

  it('reads readline input and prints output from platform run', async () => {
    const { runCli } = await import('../../../apps/cli/src/index.ts')

    let lineHandler: (input: string) => void = () => {}
    const rlOnMock = vi.fn(
      (_event: string, handler: (input: string) => void) => {
        if (_event === 'line') lineHandler = handler
      },
    )
    const rlPromptMock = vi.fn()
    const rlCloseMock = vi.fn()
    const stdoutWriteMock = vi.fn()

    runMock.mockResolvedValue({
      status: 'completed',
      output: 'task result output',
      agentId: 'orchestrator',
    })

    runCli({
      readFileSync: vi.fn().mockImplementation(() => {
        throw new Error('ENOENT')
      }) as unknown as typeof import('fs').readFileSyncSync,
      process: {
        env: { ANTHROPIC_API_KEY: 'test-key' },
        exit: exitMock,
        on: vi.fn(),
        stdout: { write: stdoutWriteMock, isTTY: true },
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
          on: rlOnMock,
          close: rlCloseMock,
          prompt: rlPromptMock,
          write: vi.fn(),
        }),
      } as unknown as typeof import('node:readline'),
    })

    expect(rlOnMock).toHaveBeenCalledWith('line', expect.any(Function))

    await lineHandler('my task')

    expect(runMock).toHaveBeenCalledWith('my task', expect.any(AbortSignal), expect.any(Function), expect.any(Function), expect.any(Function), expect.any(Function))
    expect(stdoutWriteMock).toHaveBeenCalledWith(
      expect.stringContaining('task result output'),
    )
    expect(rlPromptMock).toHaveBeenCalled()
  })

  it('handles failed result in readline handler', async () => {
    const { runCli } = await import('../../../apps/cli/src/index.ts')

    let lineHandler: (input: string) => void = () => {}
    const rlOnMock = vi.fn(
      (_event: string, handler: (input: string) => void) => {
        if (_event === 'line') lineHandler = handler
      },
    )
    const rlPromptMock = vi.fn()
    const stdoutWriteMock = vi.fn()

    runMock.mockResolvedValue({
      status: 'failed',
      error: 'API quota exceeded',
      agentId: 'orchestrator',
    })

    runCli({
      readFileSync: vi.fn().mockImplementation(() => {
        throw new Error('ENOENT')
      }) as unknown as typeof import('fs').readFileSyncSync,
      process: {
        env: { ANTHROPIC_API_KEY: 'test-key' },
        exit: exitMock,
        on: vi.fn(),
        stdout: { write: stdoutWriteMock, isTTY: true },
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
          on: rlOnMock,
          close: vi.fn(),
          prompt: rlPromptMock,
          write: vi.fn(),
        }),
      } as unknown as typeof import('node:readline'),
    })

    await lineHandler('some task')

    expect(stdoutWriteMock).toHaveBeenCalledWith(
      expect.stringContaining('temporarily unavailable'),
    )
    expect(rlPromptMock).toHaveBeenCalled()
  })
})
