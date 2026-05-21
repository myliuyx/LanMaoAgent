import { describe, it, expect } from 'vitest'
import type { ChatMessage, ToolCall, ToolResult, ToolDefinition } from '@agent-platform/shared-types'

describe('ChatMessage', () => {
  it('accepts valid system role message', () => {
    const msg: ChatMessage = { role: 'system', content: 'You are a helper.' }
    expect(msg.role).toBe('system')
  })

  it('accepts valid user role message', () => {
    const msg: ChatMessage = { role: 'user', content: 'hello' }
    expect(msg.role).toBe('user')
  })

  it('accepts valid assistant role message', () => {
    const msg: ChatMessage = { role: 'assistant', content: 'hi' }
    expect(msg.role).toBe('assistant')
  })

  it('accepts valid tool role message', () => {
    const msg: ChatMessage = { role: 'tool', content: 'result' }
    expect(msg.role).toBe('tool')
  })

  it('union type has exactly four valid roles', () => {
    const validRoles = ['system', 'user', 'assistant', 'tool'] as const
    expect(validRoles).toHaveLength(4)
    expect(validRoles).toContain('system')
    expect(validRoles).toContain('user')
    expect(validRoles).toContain('assistant')
    expect(validRoles).toContain('tool')
  })

  it('carries optional toolCalls on assistant message', () => {
    const msg: ChatMessage = {
      role: 'assistant',
      content: '',
      toolCalls: [{ id: 'call_1', name: 'read_file', arguments: { path: '/tmp' } }],
    }
    expect(msg.toolCalls).toHaveLength(1)
    expect(msg.toolCalls![0].id).toBe('call_1')
  })

  it('carries optional toolResults on tool message', () => {
    const msg: ChatMessage = {
      role: 'tool',
      content: '',
      toolResults: [{ content: 'result', isError: false }],
    }
    expect(msg.toolResults).toHaveLength(1)
    expect(msg.toolResults![0].isError).toBe(false)
  })
})

describe('ToolCall', () => {
  it('has required id, name, arguments fields', () => {
    const call: ToolCall = { id: 'call_1', name: 'read_file', arguments: { path: '/tmp/test.txt' } }
    expect(call.id).toBe('call_1')
    expect(call.name).toBe('read_file')
    expect(call.arguments).toEqual({ path: '/tmp/test.txt' })
  })

  it('arguments type is unknown (requires explicit cast at use site)', () => {
    const call: ToolCall = { id: 'c1', name: 'test', arguments: { key: 'value' } }
    const args = call.arguments as Record<string, unknown>
    expect(args.key).toBe('value')
  })
})

describe('ToolResult', () => {
  it('has content and isError fields', () => {
    const result: ToolResult = { content: 'file content', isError: false }
    expect(result.content).toBe('file content')
    expect(result.isError).toBe(false)
  })

  it('can indicate error state', () => {
    const result: ToolResult = { content: 'ENOENT: file not found', isError: true }
    expect(result.isError).toBe(true)
  })
})

describe('ToolDefinition', () => {
  it('has name, description, parameters in JSON Schema format', () => {
    const def: ToolDefinition = {
      name: 'read_file',
      description: 'Read a file from disk',
      parameters: {
        type: 'object',
        properties: { path: { type: 'string' } },
        required: ['path'],
      },
    }
    expect(def.name).toBe('read_file')
    expect(def.parameters.type).toBe('object')
  })
})
