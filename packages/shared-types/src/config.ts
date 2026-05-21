export interface LlmConfig {
  provider: 'anthropic' | 'openai'
  apiKey?: string
  baseUrl?: string
  timeoutSec?: number
  stream?: boolean
}

export interface AgentRuntimeParams {
  model: string
  temperature?: number
  maxTokens?: number
  contextWindow?: number
}

export interface AgentConfig {
  id: string
  name: string
  description: string
  systemPrompt: string
  tools?: string[]
  extends?: string
}

export interface SecurityConfig {
  allowedPaths?: string[]
  terminalWhitelist?: string[]
}

export interface RuntimeConfig {
  maxIterations?: number
  maxToolRetries?: number
  stmThreshold?: number
  compressionRatio?: number
  contextWindow?: number
}

export interface CliConfig {
  prompt: string
}

export interface PlatformConfig {
  llm: LlmConfig
  agents: AgentConfig[]
  defaultTools?: string[]
  agentsDir?: string
  runtime?: RuntimeConfig
  security?: SecurityConfig
  cli?: CliConfig
}

export const DEFAULT_LLM: Partial<LlmConfig> = {
  baseUrl: 'https://api.anthropic.com',
  timeoutSec: 30,
}

export const DEFAULT_AGENT_PARAMS: AgentRuntimeParams = {
  model: 'claude-sonnet-4',
  temperature: 0.2,
  maxTokens: 8192,
  contextWindow: 200000,
}

export const DEFAULT_AGENTS_DIR = '~/.agent-platform/agents'
export const DEFAULT_TOOLS: string[] = ['filesystem', 'git', 'terminal']

export const DEFAULT_CONFIG: Omit<PlatformConfig, 'llm' | 'agents'> = {
  runtime: { maxIterations: 20, stmThreshold: 50, compressionRatio: 0.8 },
  security: { allowedPaths: [], terminalWhitelist: [] },
  cli: { prompt: 'Ask me anything: ' },
}
