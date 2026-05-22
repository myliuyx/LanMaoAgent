import { execFile, exec } from 'node:child_process'
import type {
  Logger,
  ToolHandler,
  ToolDefinition,
  ToolCall,
  ToolResult,
  ToolExecutionContext,
} from '@agent-platform/shared-types'
import { consoleLogger } from '@agent-platform/shared-types'
import { checkShellInjection } from './shellSecurity.js'

/**
 * Maximum buffer size for terminal command output.
 * Set to 768KB as a compromise: large enough for real-world use cases (e.g.,
 * `git diff`, `ls -laR` on medium projects) while mitigating DoS risk from
 * unbounded memory allocation via malicious command output.
 */
const TERMINAL_MAX_BUFFER = 768 * 1024 // 768KB — balances functionality vs. security

/**
 * Check command arguments for dangerous patterns that could lead to
 * arbitrary command execution or unintended file modification.
 */
function checkCommandArgs(name: string, args: string[]): { blocked: true; reason: string } | null {
  // find -exec / -ok can execute arbitrary commands
  if (name === 'find') {
    const execIndex = args.indexOf('-exec')
    if (execIndex !== -1) {
      return { blocked: true, reason: "'find' with '-exec' is not allowed" }
    }
    const okIndex = args.indexOf('-ok')
    if (okIndex !== -1) {
      return { blocked: true, reason: "'find' with '-ok' is not allowed" }
    }
  }

  // sed -i performs in-place editing which can modify sensitive files
  if (name === 'sed') {
    for (const arg of args) {
      if (arg === '-i' || arg.startsWith('-i')) {
        return { blocked: true, reason: "'sed' with '-i' (in-place edit) is not allowed" }
      }
    }
  }

  return null
}

const DEFAULT_WHITELIST = new Set([
  'cat', 'grep', 'ls', 'echo', 'git', 'find', 'head', 'tail', 'wc',
  'sed', 'mkdir', 'cp', 'mv', 'rm', 'touch', 'chmod', 'which',
  'node', 'npx', 'tsc', 'pnpm', 'npm',
  // Common safe utilities
  'pwd', 'date', 'uname', 'whoami', 'tee', 'diff', 'sort', 'uniq',
])

// Full command patterns that are explicitly allowed (for commands with specific arguments)
const ALLOWED_COMMAND_PATTERNS = new Set([
  'pnpm install',
  'tsc --build',
  'npm run build',
  'git diff HEAD origin/main --stat',
  'git status',
  'git log',
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

/** Check if command uses shell operators that require shell execution. */
function needsShell(command: string): boolean {
  return /&&|\|\||\|/.test(command)
}

export class TerminalHandler implements ToolHandler {
  readonly id = 'terminal'
  private whitelist: Set<string>
  private logger: Logger

  constructor(whitelist?: string[], logger?: Logger) {
    this.whitelist = (whitelist && whitelist.length > 0) ? new Set(whitelist) : DEFAULT_WHITELIST
    this.logger = logger ?? consoleLogger
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

    // Shell mode: commands with &&, ||, | need shell execution
    if (needsShell(command)) {
      const firstCmd = command.trim().split(/\s+/)[0]
      if (!this.whitelist.has(firstCmd)) {
        return { content: `Command '${firstCmd}' is not allowed`, isError: true, retryable: false }
      }

      // Check each pipeline segment for always-dangerous patterns
      const segments = command.split(/\s*(?:&&|\|\||\|)\s*/)
      for (const segment of segments) {
        const danger = checkShellInjection(segment.trim())
        if (danger?.reason.startsWith('Blocked')) {
          return { content: danger.reason, isError: true, retryable: false }
        }
      }

      try {
        const output = await new Promise<string>((resolve, reject) => {
          exec(
            command,
            {
              cwd: ctx.cwd,
              timeout: 30000,
              maxBuffer: TERMINAL_MAX_BUFFER,
            },
            (err, stdout, stderr) => {
              if (err) {
                const msg = stderr ? `${stdout}\n${stderr}`.trim() : err.message || 'Unknown error'
                reject(new Error(msg))
              } else {
                resolve(stderr ? `${stdout}\n[stderr]\n${stderr}`.trim() : stdout)
              }
            },
          )
        })

        if (output.length > 10 * 1024) {
          return { content: output.slice(0, 10 * 1024) + '\n[output truncated]', isError: false }
        }
        return { content: output, isError: false }
      } catch (e) {
        let errorMessage: string
        if (e instanceof Error) {
          errorMessage = e.message || e.toString()
        } else if (typeof e === 'string') {
          errorMessage = e
        } else if (e != null && typeof e === 'object' && 'message' in e) {
          const obj = e as Record<string, unknown>
          errorMessage = String(obj.message ?? JSON.stringify(e))
        } else {
          errorMessage = `Unknown error: ${JSON.stringify(e)}`
        }

        this.logger.error('Command execution failed', { command, error: errorMessage })
        return { content: errorMessage, isError: true }
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

    // Check command arguments for dangerous patterns
    const argCheck = checkCommandArgs(name, cmdArgs)
    if (argCheck) {
      return {
        content: argCheck.reason,
        isError: true,
        retryable: false,
      }
    }

    try {
      const output = await new Promise<string>((resolve, reject) => {
        execFile(
          name,
          cmdArgs,
          {
            cwd: ctx.cwd,
            timeout: 30000,
            maxBuffer: TERMINAL_MAX_BUFFER,
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

      this.logger.error('Command execution failed', { command, error: errorMessage })
      return { content: errorMessage, isError: true }
    }
  }
}
