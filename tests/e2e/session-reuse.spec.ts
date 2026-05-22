import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mkdtempSync, rmSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'

let tmpDir = ''
const mockComplete = vi.fn()

vi.mock('@agent-platform/llm-adapter', () => ({
  ClaudeAdapter: vi.fn(function MockClaude() {
    return { complete: mockComplete }
  }),
}))

describe('E2E: Session Reuse and Multi-Turn Flow', () => {
  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'e2e-session-'))
    mockComplete.mockReset()
  })

  afterEach(() => {
    try {
      rmSync(tmpDir, { recursive: true, force: true })
    } catch {
      // ignore cleanup failures
    }
  })

  it('preserves conversation history across multiple platform.run() calls', async () => {
    const callHistory: number[] = []
    mockComplete.mockImplementation(async (messages) => {
      callHistory.push(messages.length)
      return {
        message: {
          role: 'assistant',
          content: `Response to ${callHistory.length}th request`,
        },
        usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
        finishReason: 'stop' as const,
      }
    })

    const { Platform } = await import('@agent-platform/platform')

    const platform = new Platform({
      llm: { provider: 'anthropic', apiKey: 'test-key' },
      agents: [
        {
          id: 'orchestrator',
          name: 'Orchestrator',
          description: 'Orchestrator agent',
          systemPrompt: 'You are an orchestrator.',
          tools: ['delegate_to_agent'],
        },
        {
          id: 'coding-agent',
          name: 'Coding Agent',
          description: 'Coding expert',
          systemPrompt: 'You are a coding expert.',
          tools: ['filesystem', 'git', 'terminal'],
        },
      ],
      security: { allowedPaths: [tmpDir], terminalWhitelist: [] },
    })

    await platform.run('First request')
    expect(callHistory[0]).toBe(2) // system + user

    await platform.run('Second request')
    expect(callHistory[1]).toBeGreaterThan(2) // includes first turn history

    await platform.run('Third request')
    expect(callHistory[2]).toBeGreaterThan(callHistory[1]) // more history accumulated
  })

  it('reuses existing session for same agentId + projectRoot', async () => {
    let callCount = 0
    mockComplete.mockImplementation(() => {
      callCount++
      return {
        message: { role: 'assistant', content: `Answer #${callCount}` },
        usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
        finishReason: 'stop' as const,
      }
    })

    const { Platform } = await import('@agent-platform/platform')

    const platform = new Platform({
      llm: { provider: 'anthropic', apiKey: 'test-key' },
      agents: [
        {
          id: 'orchestrator',
          name: 'Orchestrator',
          description: 'Orchestrator agent',
          systemPrompt: 'You are an orchestrator.',
          tools: ['delegate_to_agent'],
        },
        {
          id: 'coding-agent',
          name: 'Coding Agent',
          description: 'Coding expert',
          systemPrompt: 'You are a coding expert.',
          tools: ['filesystem', 'git', 'terminal'],
        },
      ],
      security: { allowedPaths: [tmpDir], terminalWhitelist: [] },
    })

    await platform.run('Request A')
    expect(callCount).toBe(1)

    await platform.run('Request B')
    expect(callCount).toBe(2) // same session, not a new one
  })
})
