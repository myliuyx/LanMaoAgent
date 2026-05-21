import { describe, it, expect } from 'vitest'
import { ToolRegistry } from '@agent-platform/tool-core'
import type {
  ToolHandler,
  ToolDefinition,
  ToolCall,
  ToolResult,
  ToolExecutionContext,
} from '@agent-platform/shared-types'

function mockHandler(
  id: string,
  tools: ToolDefinition[],
  executeFn?: (call: ToolCall) => Promise<ToolResult>,
): ToolHandler {
  return {
    id,
    getTools: () => tools,
    execute: executeFn ?? (async () => ({ content: `${id} result`, isError: false })),
  }
}

function ctx(overrides?: Partial<ToolExecutionContext>): ToolExecutionContext {
  return {
    sessionId: 'test',
    agentId: 'test',
    cwd: '/tmp',
    ...overrides,
  }
}

describe('ToolRegistry', () => {
  describe('register / getAllTools', () => {
    it('register then getAllTools reflects new tool immediately', () => {
      const registry = new ToolRegistry()
      const handler = mockHandler('fs', [
        { name: 'read_file', description: 'Read', parameters: {} },
      ])
      registry.register(handler)
      const all = registry.getAllTools()
      expect(all).toHaveLength(1)
      expect(all[0].name).toBe('read_file')
    })

    it('getAllTools returns tools from all registered handlers', () => {
      const registry = new ToolRegistry()
      registry.register(
        mockHandler('fs', [
          { name: 'read_file', description: 'Read', parameters: {} },
          { name: 'write_file', description: 'Write', parameters: {} },
        ]),
      )
      registry.register(
        mockHandler('git', [
          { name: 'git_diff', description: 'Diff', parameters: {} },
        ]),
      )
      expect(registry.getAllTools()).toHaveLength(3)
    })
  })

  describe('execute', () => {
    it('calls correct handler and returns its result', async () => {
      const registry = new ToolRegistry()
      const handler = mockHandler('fs', [
        { name: 'read_file', description: 'Read', parameters: {} },
      ], async (call) => ({
        content: `processed ${call.name}`,
        isError: false,
      }))
      registry.register(handler)
      const result = await registry.execute(
        { id: '1', name: 'read_file', arguments: { path: '/tmp/f' } },
        ctx(),
      )
      expect(result.content).toBe('processed read_file')
      expect(result.isError).toBeFalsy()
    })

    it('for unknown tool returns isError with Unknown tool message', async () => {
      const registry = new ToolRegistry()
      const result = await registry.execute(
        { id: '1', name: 'nonexistent', arguments: {} },
        ctx(),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('Unknown tool')
    })

    it('handler error is caught and returned as isError with Tool error prefix', async () => {
      const registry = new ToolRegistry()
      registry.register(
        mockHandler('broken', [
          { name: 'crash', description: 'Crash', parameters: {} },
        ], async () => {
          throw new Error('oops')
        }),
      )
      const result = await registry.execute(
        { id: '1', name: 'crash', arguments: {} },
        ctx(),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('Tool error: oops')
    })
  })

  describe('allowedPaths', () => {
    const writeToolDef = { name: 'write_file', description: 'Write', parameters: {} }

    it('blocks write path outside allowed directory', async () => {
      const registry = new ToolRegistry()
      registry.register(
        mockHandler('fs', [writeToolDef], async (call) => ({
          content: `${call.name} ok`,
          isError: false,
        })),
      )
      const result = await registry.execute(
        { id: '1', name: 'write_file', arguments: { path: '/etc/passwd' } },
        ctx({ allowedPaths: ['/tmp/allowed'] }),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('Access denied')
    })

    it('allows path inside allowed directory', async () => {
      const registry = new ToolRegistry()
      registry.register(
        mockHandler('fs', [writeToolDef], async (call) => ({
          content: `${call.name} ok`,
          isError: false,
        })),
      )
      const result = await registry.execute(
        { id: '1', name: 'write_file', arguments: { path: '/tmp/allowed/test.txt' } },
        ctx({ allowedPaths: ['/tmp/allowed'] }),
      )
      expect(result.isError).toBeFalsy()
      expect(result.content).toBe('write_file ok')
    })

    it('extracts path from nested arguments', async () => {
      const registry = new ToolRegistry()
      registry.register(
        mockHandler('fs', [writeToolDef], async () => ({
          content: `ok`,
          isError: false,
        })),
      )
      const result = await registry.execute(
        {
          id: '1',
          name: 'write_file',
          arguments: { settings: { path: '/etc/secret' } },
        },
        ctx({ allowedPaths: ['/tmp'] }),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('Access denied')
    })

    it('no-op when allowedPaths is undefined', async () => {
      const registry = new ToolRegistry()
      registry.register(
        mockHandler('fs', [writeToolDef], async (call) => ({
          content: `${call.name} ok`,
          isError: false,
        })),
      )
      const result = await registry.execute(
        { id: '1', name: 'write_file', arguments: { path: '/any/path' } },
        ctx(), // no allowedPaths
      )
      expect(result.isError).toBeFalsy()
    })
  })
})
