export interface ChatResponse {
  message: { role: 'assistant'; content?: string; toolCalls?: import('./chat.js').ToolCall[] }
  usage: TokenUsage
  finishReason: 'stop' | 'tool_calls' | 'length' | 'content_filter'
}

export interface TokenUsage {
  promptTokens: number
  completionTokens: number
  totalTokens: number
}

export interface AgentResult {
  status: 'completed' | 'max_iterations_reached' | 'failed' | 'aborted'
  output?: string
  agentId: string
  error?: string
}
