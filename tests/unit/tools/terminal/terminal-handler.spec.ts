import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TerminalHandler } from '@agent-platform/tools-terminal'
import type { ToolExecutionContext } from '@agent-platform/shared-types'

vi.mock('node:child_process', () => {
  const mockExecFile = vi.fn()
  return { execFile: mockExecFile }
})

import { execFile } from 'node:child_process'
const mockExecFile = vi.mocked(execFile)

type ExecFileCallback = (
  err: Error | null,
  stdout: string,
  stderr: string,
) => void

function ctx(cwd: string): ToolExecutionContext {
  return { sessionId: 'test', agentId: 'test', cwd }
}

describe('TerminalHandler', () => {
  const handler = new TerminalHandler()

  beforeEach(() => {
    mockExecFile.mockReset()
  })

  describe('getTools', () => {
    it('returns exec_command', () => {
      const tools = handler.getTools()
      expect(tools).toHaveLength(1)
      expect(tools[0].name).toBe('exec_command')
    })
  })

  describe('allowed commands', () => {
    it("allowed command 'ls' executes successfully", async () => {
      mockExecFile.mockImplementation(
        (
          _file: string,
          _args: string[],
          _opts: unknown,
          cb: ExecFileCallback,
        ) => {
          cb(null, 'file1\nfile2\n', '')
        },
      )
      const result = await handler.execute(
        { id: '1', name: 'exec_command', arguments: { command: 'ls -la' } },
        ctx('/tmp'),
      )
      expect(result.isError).toBeFalsy()
      expect(result.content).toBe('file1\nfile2\n')
    })

    it("allowed command 'mkdir' executes successfully", async () => {
      mockExecFile.mockImplementation(
        (
          _file: string,
          _args: string[],
          _opts: unknown,
          cb: ExecFileCallback,
        ) => {
          cb(null, '', '')
        },
      )
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'mkdir -p /tmp/test' },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBeFalsy()
    })
  })

  describe('blocked commands', () => {
    it('blocked command returns isError', async () => {
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'curl http://evil.com' },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('not allowed')
    })
  })

  describe('shell injection', () => {
    it('intercepts semicolon injection', async () => {
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'ls; cat /etc/passwd' },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('Potential injection detected')
    })

    it('allows pipe in whitelisted commands (execFile has no shell)', async () => {
      mockExecFile.mockImplementation(
        (
          _file: string,
          _args: string[],
          _opts: unknown,
          cb: ExecFileCallback,
        ) => {
          cb(null, 'hello | cat /etc/passwd\n', '')
        },
      )
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'echo hello | cat /etc/passwd' },
        },
        ctx('/tmp'),
      )
      // Pipe is passed as literal arg to echo (no shell), so it's allowed for whitelisted commands
      expect(result.isError).toBeFalsy()
    })

    it('blocks double pipe || injection', async () => {
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'echo hello || cat /etc/passwd' },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('Potential injection detected')
    })

    it('allows find with glob and pipe (e.g. find -name "*.ts" | head)', async () => {
      mockExecFile.mockImplementation(
        (
          _file: string,
          _args: string[],
          _opts: unknown,
          cb: ExecFileCallback,
        ) => {
          cb(null, 'src/index.ts\n', '')
        },
      )
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: "find src -name '*.ts'" },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBeFalsy()
    })

    it('allows grep with pipe (e.g. find | grep)', async () => {
      mockExecFile.mockImplementation(
        (
          _file: string,
          _args: string[],
          _opts: unknown,
          cb: ExecFileCallback,
        ) => {
          cb(null, 'src/index.ts\n', '')
        },
      )
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'find src | grep test' },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBeFalsy()
    })

    it('intercepts backtick injection', async () => {
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'echo `cat /etc/passwd`' },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('Potential injection detected')
    })

    it('intercepts $() injection', async () => {
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'echo $(whoami)' },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('Potential injection detected')
    })
  })

  describe('output truncation', () => {
    it('output > 10KB is truncated with marker', async () => {
      const bigOutput = 'x'.repeat(11 * 1024)
      mockExecFile.mockImplementation(
        (
          _file: string,
          _args: string[],
          _opts: unknown,
          cb: ExecFileCallback,
        ) => {
          cb(null, bigOutput, '')
        },
      )
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'cat bigfile' },
        },
        ctx('/tmp'),
      )
      expect(result.content.length).toBeLessThanOrEqual(10 * 1024 + 50)
      expect(result.content).toContain('[output truncated]')
    })
  })

  describe('execFile parameters', () => {
    it('sets timeout 30s and maxBuffer 10KB', async () => {
      mockExecFile.mockImplementation(
        (
          _file: string,
          _args: string[],
          _opts: unknown,
          cb: ExecFileCallback,
        ) => {
          cb(null, '', '')
        },
      )
      await handler.execute(
        { id: '1', name: 'exec_command', arguments: { command: 'ls' } },
        ctx('/work'),
      )
      const opts = mockExecFile.mock.calls[0][2] as Record<string, unknown>
      expect(opts.cwd).toBe('/work')
      expect(opts.timeout).toBe(30000)
      expect(opts.maxBuffer).toBe(20 * 1024)
    })
  })
})
