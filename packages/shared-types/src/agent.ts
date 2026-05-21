import type { ToolCall, ToolResult, ToolDefinition } from './chat.js'

export interface ToolHandler {
  readonly id: string
  getTools(): ToolDefinition[]
  execute(call: ToolCall, ctx: ToolExecutionContext): Promise<ToolResult>
}

export interface ToolExecutionContext {
  sessionId: string
  agentId: string
  cwd: string
  depth?: number
  allowedPaths?: string[]
  onToolStart?: (call: ToolCall, agentId: string) => void
  onToolFinish?: (call: ToolCall, result: ToolResult, agentId: string) => void
  onToolRetry?: (call: ToolCall, attempt: number, maxAttempts: number, error: string, agentId: string) => void
}

export interface Agent {
  readonly id: string
  readonly name: string
  description: string
  systemPrompt: string
  model: string
  temperature?: number
  maxTokens?: number
  contextWindow?: number
  readonly tools: ToolHandler[]
}
