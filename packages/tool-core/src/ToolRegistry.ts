import { realpathSync } from 'node:fs'
import { resolve } from 'node:path'
import type {
  Logger,
  ToolHandler,
  ToolDefinition,
  ToolCall,
  ToolResult,
  ToolExecutionContext,
} from '@agent-platform/shared-types'
import { consoleLogger } from '@agent-platform/shared-types'

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

function extractPathValues(
  obj: unknown,
  paths: string[],
  depth = 0,
): void {
  if (depth > 20 || !obj || typeof obj !== 'object') return
  for (const [key, value] of Object.entries(obj)) {
    if ((key === 'path' || key === 'filepath') && typeof value === 'string') {
      paths.push(value)
    } else if (typeof value === 'object' && value !== null) {
      extractPathValues(value, paths, depth + 1)
    }
  }
}

function shouldRetry(msg: string): boolean {
  const lower = msg.toLowerCase()
  if (/enoent|eacces|eperm|eisdir|enotdir|eexist/.test(lower)) return false
  return true
}

function checkAllowed(args: unknown, allowedPaths?: string[]): string | null {
  if (!allowedPaths || allowedPaths.length === 0) return null
  const foundPaths: string[] = []
  extractPathValues(args, foundPaths)
  for (const p of foundPaths) {
    let resolved: string
    try {
      resolved = resolve(p)
      // Resolve symlinks to prevent symlink-based path traversal attacks
      resolved = realpathSync(resolved)
    } catch {
      resolved = resolve(p)
    }
    let ok = false
    for (const ap of allowedPaths) {
      try {
        const realAllowed = realpathSync(resolve(ap))
        if (resolved === realAllowed || resolved.startsWith(realAllowed + '/')) {
          ok = true
          break
        }
      } catch {
        // If allowed path doesn't exist, fall back to plain resolve
        if (resolved.startsWith(resolve(ap))) {
          ok = true
          break
        }
      }
    }
    if (!ok) {
      return `Access denied: path '${p}' is not allowed`
    }
  }
  return null
}

export interface ToolRegistryInterface {
  register(handler: ToolHandler): void
  getAllTools(): ToolDefinition[]
  execute(call: ToolCall, ctx: ToolExecutionContext): Promise<ToolResult>
}

export class ToolRegistry implements ToolRegistryInterface {
  private handlers = new Map<string, ToolHandler>()
  private toolToHandler = new Map<string, ToolHandler>()
  private logger: Logger

  constructor(logger?: Logger) {
    this.logger = logger ?? consoleLogger
  }

  register(handler: ToolHandler): void {
    this.handlers.set(handler.id, handler)
    for (const tool of handler.getTools()) {
      this.toolToHandler.set(tool.name, handler)
    }
  }

  getAllTools(): ToolDefinition[] {
    return Array.from(this.handlers.values()).flatMap((h) => h.getTools())
  }

  async execute(
    call: ToolCall,
    ctx: ToolExecutionContext,
  ): Promise<ToolResult> {
    const denied = checkAllowed(call.arguments, ctx.allowedPaths)
    if (denied) {
      return { content: denied, isError: true, retryable: false }
    }

    const handler = this.toolToHandler.get(call.name)
    if (!handler) {
      return { content: `Unknown tool: ${call.name}`, isError: true, retryable: false }
    }

    try {
      return await handler.execute(call, ctx)
    } catch (e) {
      const msg = safeErrorMessage(e)
      return {
        content: `Tool error: ${msg}`,
        isError: true,
        retryable: shouldRetry(msg),
      }
    }
  }
}
