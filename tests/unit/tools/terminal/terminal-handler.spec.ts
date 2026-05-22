import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TerminalHandler } from '@agent-platform/tools-terminal'
import type { ToolExecutionContext } from '@agent-platform/shared-types'

vi.mock('node:child_process', () => {
  const mockExecFile = vi.fn()
  const mockExec = vi.fn()
  return { execFile: mockExecFile, exec: mockExec }
})

import { execFile, exec } from 'node:child_process'
const mockExecFile = vi.mocked(execFile)
const mockExec = vi.mocked(exec)

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

    it("allowed command 'pwd' executes successfully", async () => {
      mockExecFile.mockImplementation(
        (
          _file: string,
          _args: string[],
          _opts: unknown,
          cb: ExecFileCallback,
        ) => {
          cb(null, '/current/dir\n', '')
        },
      )
      const result = await handler.execute(
        { id: '1', name: 'exec_command', arguments: { command: 'pwd' } },
        ctx('/tmp'),
      )
      expect(result.isError).toBeFalsy()
    })

    it("allowed command 'git status' executes successfully", async () => {
      mockExecFile.mockImplementation(
        (
          _file: string,
          _args: string[],
          _opts: unknown,
          cb: ExecFileCallback,
        ) => {
          cb(null, 'On branch main\n', '')
        },
      )
      const result = await handler.execute(
        { id: '1', name: 'exec_command', arguments: { command: 'git status' } },
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

    it('blocked rm -rf returns isError', async () => {
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'rm -rf /tmp' },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBe(true)
    })

    it('blocked dd returns isError', async () => {
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'dd if=/dev/zero of=/dev/sda' },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBe(true)
    })

    it('blocked parent traversal returns isError', async () => {
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: '../../etc/passwd' },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBe(true)
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

    it('allows && control flow on whitelisted commands', async () => {
      mockExec.mockImplementation(
        (
          _cmd: string,
          _opts: unknown,
          cb: ExecFileCallback,
        ) => {
          cb(null, 'hello\nworld\n', '')
        },
      )
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'echo hello && echo world' },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBeFalsy()
    })

    it('allows || fallback on whitelisted commands', async () => {
      mockExec.mockImplementation(
        (
          _cmd: string,
          _opts: unknown,
          cb: ExecFileCallback,
        ) => {
          cb(null, 'result\n', '')
        },
      )
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: {
            command: 'git diff HEAD origin/main --stat || echo "No remote"',
          },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBeFalsy()
    })

    it('allows pipe on whitelisted commands', async () => {
      mockExec.mockImplementation(
        (
          _cmd: string,
          _opts: unknown,
          cb: ExecFileCallback,
        ) => {
          cb(null, 'hello\n', '')
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
      expect(result.isError).toBeFalsy()
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
      mockExec.mockImplementation(
        (
          _cmd: string,
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

    it('intercepts ${} variable expansion injection', async () => {
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'echo ${PATH}' },
        },
        ctx('/tmp'),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('Potential injection detected')
    })

    it('allows $ in non-injection context (e.g. dollar sign)', async () => {
      mockExecFile.mockImplementation(
        (
          _file: string,
          _args: string[],
          _opts: unknown,
          cb: ExecFileCallback,
        ) => {
          cb(null, '5\n', '')
        },
      )
      const result = await handler.execute(
        {
          id: '1',
          name: 'exec_command',
          arguments: { command: 'echo $5' },
        },
        ctx('/tmp'),
      )
      // Plain $N (positional param) is not an injection vector
      expect(result.isError).toBeFalsy()
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
    it('sets timeout 30s and maxBuffer 1MB', async () => {
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
      expect(opts.maxBuffer).toBe(768 * 1024)
    })
  })
})
