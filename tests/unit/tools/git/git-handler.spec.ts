import { describe, it, expect, vi, beforeEach } from 'vitest'
import { GitHandler } from '@agent-platform/tools-git'
import type { ToolExecutionContext } from '@agent-platform/shared-types'

vi.mock('node:child_process', () => {
  const mockExecFile = vi.fn()
  return { execFile: mockExecFile }
})

import { execFile } from 'node:child_process'
const mockExecFile = vi.mocked(execFile)

type ExecFileCallback = (err: Error | null, stdout: string, stderr: string) => void

function ctx(cwd: string): ToolExecutionContext {
  return { sessionId: 'test', agentId: 'test', cwd }
}

describe('GitHandler', () => {
  const handler = new GitHandler()

  beforeEach(() => {
    mockExecFile.mockReset()
  })

  describe('getTools', () => {
    it('returns git_diff and git_status', () => {
      const tools = handler.getTools()
      expect(tools).toHaveLength(2)
      const names = tools.map((t) => t.name)
      expect(names).toContain('git_diff')
      expect(names).toContain('git_status')
    })
  })

  describe('git_diff', () => {
    it("returns 'No changes' when no diffs", async () => {
      mockExecFile.mockImplementation(
        (_file: string, _args: string[], _opts: unknown, cb: ExecFileCallback) => {
          cb(null, '', '')
        },
      )
      const result = await handler.execute(
        { id: '1', name: 'git_diff', arguments: {} },
        ctx('/repo'),
      )
      expect(result.content).toBe('No changes')
      expect(result.isError).toBeFalsy()
    })

    it('returns diff output from cached and working tree', async () => {
      let callCount = 0
      mockExecFile.mockImplementation(
        (_file: string, _args: string[], _opts: unknown, cb: ExecFileCallback) => {
          callCount++
          cb(null, callCount === 1 ? 'cached diff\n' : 'working diff\n', '')
        },
      )
      const result = await handler.execute(
        { id: '1', name: 'git_diff', arguments: {} },
        ctx('/repo'),
      )
      expect(result.content).toContain('cached diff')
      expect(result.content).toContain('working diff')
      expect(mockExecFile).toHaveBeenCalledTimes(2)
    })

    it('passes cwd and timeout 10s to execFile', async () => {
      mockExecFile.mockImplementation(
        (_file: string, _args: string[], _opts: unknown, cb: ExecFileCallback) => {
          cb(null, '', '')
        },
      )
      await handler.execute(
        { id: '1', name: 'git_diff', arguments: {} },
        ctx('/my/repo'),
      )
      expect(mockExecFile).toHaveBeenCalled()
      const callOpts = mockExecFile.mock.calls[0][2] as Record<string, unknown>
      expect(callOpts.cwd).toBe('/my/repo')
      expect(callOpts.timeout).toBe(10000)
    })
  })

  describe('git_status', () => {
    it('runs git status -sb in correct working directory', async () => {
      mockExecFile.mockImplementation(
        (_file: string, _args: string[], _opts: unknown, cb: ExecFileCallback) => {
          cb(null, '## main\n', '')
        },
      )
      const result = await handler.execute(
        { id: '1', name: 'git_status', arguments: {} },
        ctx('/my/repo2'),
      )
      expect(result.content).toBe('## main\n')
      expect(mockExecFile).toHaveBeenCalledWith(
        'git',
        ['status', '-sb'],
        expect.objectContaining({ cwd: '/my/repo2', timeout: 10000 }),
        expect.any(Function),
      )
    })
  })

  describe('cwd validation', () => {
    it('non-absolute cwd returns isError: true', async () => {
      const result = await handler.execute(
        { id: '1', name: 'git_status', arguments: {} },
        ctx('relative/path'),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('Invalid working directory')
      expect(mockExecFile).not.toHaveBeenCalled()
    })
  })
})
