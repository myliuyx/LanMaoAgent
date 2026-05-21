import { execFile } from 'node:child_process'
import type {
  ToolHandler,
  ToolDefinition,
  ToolCall,
  ToolResult,
  ToolExecutionContext,
} from '@agent-platform/shared-types'
import { checkShellInjection } from './shellSecurity.js'

const DEFAULT_WHITELIST = new Set([
  'cat', 'grep', 'ls', 'echo', 'git', 'find', 'head', 'tail', 'wc',
  'sed', 'mkdir', 'cp', 'mv', 'rm', 'touch', 'chmod', 'which',
  'node', 'npx', 'tsc', 'pnpm', 'npm',
])

// Full command patterns that are explicitly allowed (for commands with specific arguments)
const ALLOWED_COMMAND_PATTERNS = new Set([
  'pnpm install',
  'tsc --build',
  'npm run build',
])

function parseCommand(cmd: string): { name: string; args: string[] } {
  const trimmed = cmd.trim()
  const parts: string[] = []
  let current = ''
  let inQuote = false
  let quoteChar = '' as '"' | "'" | ''
  for (let i = 0; i < trimmed.length; i++) {
    const ch = trimmed[i]
    const prev = i > 0 ? trimmed[i - 1] : ''

    // Handle escaped quotes
    if (prev === '\\' && (ch === '"' || ch === "'")) {
      current += ch
      continue
    }

    if ((ch === '"' || ch === "'") && quoteChar === '') {
      inQuote = true
      quoteChar = ch
      continue
    }
    if (ch === quoteChar && inQuote) {
      inQuote = false
      quoteChar = ''
      continue
    }

    if (inQuote) {
      current += ch
    } else if (ch === ' ') {
      if (current) {
        parts.push(current)
        current = ''
      }
    } else {
      current += ch
    }
  }
  if (current) parts.push(current)
  return { name: parts[0] ?? '', args: parts.slice(1) }
}

export class TerminalHandler implements ToolHandler {
  readonly id = 'terminal'
  private whitelist: Set<string>

  constructor(whitelist?: string[]) {
    this.whitelist = whitelist ? new Set(whitelist) : DEFAULT_WHITELIST
  }

  getTools(): ToolDefinition[] {
    return [
      {
        name: 'exec_command',
        description: 'Execute a shell command (whitelisted commands only)',
        parameters: {
          type: 'object',
          properties: {
            command: {
              type: 'string',
              description: 'Shell command to execute',
            },
          },
          required: ['command'],
        },
      },
    ]
  }

  async execute(call: ToolCall, ctx: ToolExecutionContext): Promise<ToolResult> {
    const args = call.arguments as Record<string, string>
    const command = args['command']
    if (!command) {
      return { content: 'No command provided', isError: true, retryable: false }
    }

    // Check for shell injection and always-dangerous patterns
    const injection = checkShellInjection(command)
    if (injection) {
      return {
        content: injection.reason,
        isError: true,
        retryable: false,
      }
    }

    const { name, args: cmdArgs } = parseCommand(command)

    // Check if the full command pattern is explicitly allowed
    const fullCommand = `${name} ${cmdArgs.join(' ')}`.trim()
    if (!ALLOWED_COMMAND_PATTERNS.has(fullCommand) && !this.whitelist.has(name)) {
      return {
        content: `Command '${fullCommand}' is not allowed`,
        isError: true,
        retryable: false,
      }
    }

    // Check for dangerous flag combinations (even on whitelisted commands)
    const danger = checkShellInjection(fullCommand)
    if (danger?.reason.startsWith('Blocked')) {
      return { content: danger.reason, isError: true, retryable: false }
    }

    try {
      const output = await new Promise<string>((resolve, reject) => {
        execFile(
          name,
          cmdArgs,
          {
            cwd: ctx.cwd,
            timeout: 30000,
            maxBuffer: 20 * 1024,
          },
          (err, stdout, stderr) => {
            if (err) {
              reject(err)
            } else {
              const result = stderr ? `${stdout}\n[stderr]\n${stderr}`.trim() : stdout
              resolve(result)
            }
          },
        )
      })

      if (output.length > 10 * 1024) {
        return {
          content: output.slice(0, 10 * 1024) + '\n[output truncated]',
          isError: false,
        }
      }

      return { content: output, isError: false }
    } catch (e) {
      // Robust error message extraction - handle non-Error objects
      let errorMessage: string
      if (e instanceof Error) {
        errorMessage = e.message || e.toString()
      } else if (typeof e === 'string') {
        errorMessage = e
      } else if (e != null && typeof e === 'object' && 'message' in e) {
        // Node.js style error objects (e.g., from execFile callback)
        const obj = e as Record<string, unknown>
        errorMessage = String(obj.message ?? JSON.stringify(e))
      } else {
        errorMessage = `Unknown error: ${JSON.stringify(e)}`
      }

      // eslint-disable-next-line no-console
      console.error(`[TerminalHandler] Command execution failed:`, command, errorMessage)
      return { content: errorMessage, isError: true }
    }
  }
}
