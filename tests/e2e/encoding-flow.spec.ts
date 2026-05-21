import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mkdtempSync, existsSync, readFileSync, rmSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'

let tmpDir = ''
const mockComplete = vi.fn()

vi.mock('@agent-platform/llm-adapter', () => ({
  ClaudeAdapter: vi.fn(function MockClaude() {
    return { complete: mockComplete }
  }),
}))

describe('E2E: Full Coding Flow', () => {
  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'e2e-flow-'))
    mockComplete.mockReset()
  })

  afterEach(() => {
    try {
      rmSync(tmpDir, { recursive: true, force: true })
    } catch {
      // ignore cleanup failures
    }
  })

  it('platform.run() delegates to coding agent, creates a file, returns result', async () => {
    let callCount = 0
    mockComplete.mockImplementation(() => {
      callCount++
      switch (callCount) {
        case 1: {
          return {
            message: {
              role: 'assistant',
              content: '',
              toolCalls: [
                {
                  id: 'call-orch-1',
                  name: 'delegate_to_agent',
                  arguments: {
                    agentId: 'coding-agent',
                    task: 'Create a quickSort function',
                  },
                },
              ],
            },
            usage: { promptTokens: 50, completionTokens: 10, totalTokens: 60 },
            finishReason: 'tool_calls' as const,
          }
        }
        case 2: {
          const filePath = join(tmpDir, 'sort.ts')
          return {
            message: {
              role: 'assistant',
              content: '',
              toolCalls: [
                {
                  id: 'call-coding-1',
                  name: 'write_file',
                  arguments: {
                    path: filePath,
                    content:
                      'function quickSort(arr: number[]): number[] {\n  if (arr.length <= 1) return arr;\n  const pivot = arr[0];\n  const left = arr.slice(1).filter(x => x < pivot);\n  const right = arr.slice(1).filter(x => x >= pivot);\n  return [...quickSort(left), pivot, ...quickSort(right)];\n}',
                  },
                },
              ],
            },
            usage: { promptTokens: 100, completionTokens: 30, totalTokens: 130 },
            finishReason: 'tool_calls' as const,
          }
        }
        case 3: {
          return {
            message: {
              role: 'assistant',
              content: 'File written successfully!',
            },
            usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
            finishReason: 'stop' as const,
          }
        }
        default: {
          return {
            message: {
              role: 'assistant',
              content: 'Task completed via coding agent.',
            },
            usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 },
            finishReason: 'stop' as const,
          }
        }
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
          systemPrompt: 'You are an orchestrator',
          tools: ['delegate_to_agent'],
        },
        {
          id: 'coding-agent',
          name: 'Coding Agent',
          description: 'Coding expert',
          systemPrompt: 'You are a coding expert',
          tools: ['filesystem', 'git', 'terminal'],
        },
      ],
      security: { allowedPaths: [tmpDir], terminalWhitelist: [] },
    })

    const result = await platform.run('Create a quickSort function')

    expect(result.status).toBe('completed')
    expect(result.output).toBeTruthy()

    const filePath = join(tmpDir, 'sort.ts')
    expect(existsSync(filePath)).toBe(true)
    const content = readFileSync(filePath, 'utf-8')
    expect(content).toContain('quickSort')
  })
})
