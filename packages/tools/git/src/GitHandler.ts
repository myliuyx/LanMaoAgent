import { execFile } from 'node:child_process'
import { isAbsolute } from 'node:path'
import type {
  ToolHandler,
  ToolDefinition,
  ToolCall,
  ToolResult,
  ToolExecutionContext,
} from '@agent-platform/shared-types'

/** Safely extract error message from unknown exception value */
function safeErrorMessage(e: unknown): string {
  if (e instanceof Error) return e.message || e.toString()
  if (typeof e === 'string') return e
  if (e != null && typeof e === 'object' && 'message' in e) {
    const obj = e as Record<string, unknown>
    return String(obj.message ?? JSON.stringify(e))
  }
  return `Unknown error: ${JSON.stringify(e)}`
}

function execGit(
  args: string[],
  cwd: string,
  timeout: number,
): Promise<string> {
  return new Promise((resolve, reject) => {
    execFile(
      'git',
      args,
      { cwd, timeout },
      (err, stdout, stderr) => {
        if (err) {
          reject(err)
        } else {
          const output = stderr ? `${stdout}\n[stderr]\n${stderr}`.trim() : stdout
          resolve(output)
        }
      },
    )
  })
}

export class GitHandler implements ToolHandler {
  readonly id = 'git'

  getTools(): ToolDefinition[] {
    return [
      {
        name: 'git_diff',
        description: 'Show git diff (cached + working tree)',
        parameters: {
          type: 'object',
          properties: {},
          required: [],
        },
      },
      {
        name: 'git_status',
        description: 'Show git status (short format)',
        parameters: {
          type: 'object',
          properties: {},
          required: [],
        },
      },
    ]
  }

  async execute(call: ToolCall, ctx: ToolExecutionContext): Promise<ToolResult> {
    if (!isAbsolute(ctx.cwd)) {
      return {
        content: 'Invalid working directory',
        isError: true,
        retryable: false,
      }
    }

    const cwd = ctx.cwd
    const timeout = 10000

    try {
      switch (call.name) {
        case 'git_diff': {
          const [cached, working] = await Promise.all([
            execGit(['diff', '--cached'], cwd, timeout),
            execGit(['diff'], cwd, timeout),
          ])
          const output = (cached + working).trim()
          return {
            content: output || 'No changes',
            isError: false,
          }
        }
        case 'git_status': {
          const output = await execGit(['status', '-sb'], cwd, timeout)
          return { content: output, isError: false }
        }
        default:
          return { content: `Unknown tool: ${call.name}`, isError: true, retryable: false }
      }
    } catch (e) {
      return { content: safeErrorMessage(e), isError: true }
    }
  }
}
