import { describe, it, expect } from 'vitest'
import type {
  PlatformConfig,
  LlmConfig,
  AgentConfig,
  AgentRuntimeParams,
  SecurityConfig,
  RuntimeConfig,
  CliConfig,
} from '@agent-platform/shared-types'

describe('LlmConfig', () => {
  it('has provider and apiKey as required fields', () => {
    const config: LlmConfig = { provider: 'anthropic', apiKey: 'sk-xxx' }
    expect(config.provider).toBe('anthropic')
    expect(config.apiKey).toBe('sk-xxx')
  })

  it('baseUrl and timeoutSec are optional', () => {
    const config: LlmConfig = { provider: 'anthropic', apiKey: 'key' }
    expect(config.baseUrl).toBeUndefined()
    expect(config.timeoutSec).toBeUndefined()
  })

  it('baseUrl and timeoutSec can be set', () => {
    const config: LlmConfig = {
      provider: 'anthropic',
      apiKey: 'key',
      baseUrl: 'https://custom.anthropic.com',
      timeoutSec: 60,
    }
    expect(config.baseUrl).toMatch(/^https?:\/\//)
    expect(config.timeoutSec).toBe(60)
  })
})

describe('AgentRuntimeParams', () => {
  it('has model as required, others optional', () => {
    const params: AgentRuntimeParams = { model: 'claude-sonnet-4' }
    expect(params.model).toBe('claude-sonnet-4')
    expect(params.temperature).toBeUndefined()
    expect(params.maxTokens).toBeUndefined()
    expect(params.contextWindow).toBeUndefined()
  })

  it('all fields can be set', () => {
    const params: AgentRuntimeParams = {
      model: 'claude-sonnet-4',
      temperature: 0.2,
      maxTokens: 8192,
      contextWindow: 200000,
    }
    expect(params.temperature).toBe(0.2)
    expect(params.maxTokens).toBe(8192)
    expect(params.contextWindow).toBe(200000)
  })
})

describe('AgentConfig', () => {
  it('has required fields for agent definition', () => {
    const config: AgentConfig = {
      id: 'coding-agent',
      name: '编码专家',
      description: '负责编写、修改、调试代码',
      systemPrompt: '你是资深开发者。',
    }
    expect(config.id).toBe('coding-agent')
    expect(config.name).toBe('编码专家')
  })

  it('does not contain handler references (pure JSON data)', () => {
    const config: AgentConfig = {
      id: 'orchestrator',
      name: '编排者',
      description: '',
      systemPrompt: '',
    }
    expect(config).not.toHaveProperty('tools')
  })
})

describe('SecurityConfig', () => {
  it('all fields are optional', () => {
    const config: SecurityConfig = {}
    expect(config.allowedPaths).toBeUndefined()
    expect(config.terminalWhitelist).toBeUndefined()
  })

  it('can restrict allowed paths and terminal commands', () => {
    const config: SecurityConfig = {
      allowedPaths: ['/home/project'],
      terminalWhitelist: ['ls', 'cat', 'git'],
    }
    expect(config.allowedPaths).toHaveLength(1)
  })
})

describe('RuntimeConfig', () => {
  it('all fields are optional', () => {
    const config: RuntimeConfig = {}
    expect(config.maxIterations).toBeUndefined()
    expect(config.stmThreshold).toBeUndefined()
    expect(config.compressionRatio).toBeUndefined()
  })

  it('can set compressionRatio for token budget', () => {
    const config: RuntimeConfig = { compressionRatio: 0.85 }
    expect(config.compressionRatio).toBe(0.85)
  })
})

describe('CliConfig', () => {
  it('has prompt field', () => {
    const config: CliConfig = { prompt: 'Ask me anything: ' }
    expect(config.prompt).toContain('Ask me')
  })
})

describe('PlatformConfig', () => {
  it('has llm and agents as required', () => {
    const config: PlatformConfig = {
      llm: { provider: 'anthropic', apiKey: 'key' },
      agents: [{ id: 'test', name: 'T', description: '', systemPrompt: '' }],
    }
    expect(config.llm.apiKey).toBe('key')
    expect(config.agents).toHaveLength(1)
  })

  it('runtime, security, cli are optional', () => {
    const config: PlatformConfig = {
      llm: { provider: 'anthropic', apiKey: 'key' },
      agents: [],
    }
    expect(config.runtime).toBeUndefined()
    expect(config.security).toBeUndefined()
    expect(config.cli).toBeUndefined()
  })
})
