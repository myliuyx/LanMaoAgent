export interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
  toolCalls?: ToolCall[]
  toolResults?: ToolResult[]
}

export interface ToolCall {
  id: string
  name: string
  arguments: unknown
}

export interface ToolResult {
  content: string
  isError: boolean
  toolCallId?: string
  retryable?: boolean
  /** Optional metadata (e.g., truncation info, performance hints) */
  metadata?: Record<string, unknown>
}

export interface ToolDefinition {
  name: string
  description: string
  parameters: Record<string, unknown>
}
