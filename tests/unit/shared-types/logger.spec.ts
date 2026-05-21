import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { Logger } from '@agent-platform/shared-types'
import { consoleLogger } from '@agent-platform/shared-types'

describe('Logger interface', () => {
  it('has info, warn, error, debug methods', () => {
    const logger: Logger = {
      info: () => {},
      warn: () => {},
      error: () => {},
      debug: () => {},
    }
    expect(typeof logger.info).toBe('function')
    expect(typeof logger.warn).toBe('function')
    expect(typeof logger.error).toBe('function')
    expect(typeof logger.debug).toBe('function')
  })

  it('methods accept optional meta parameter', () => {
    const logger: Logger = {
      info: (_msg: string, _meta?: Record<string, unknown>) => {},
      warn: (_msg: string, _meta?: Record<string, unknown>) => {},
      error: (_msg: string, _meta?: Record<string, unknown>) => {},
      debug: (_msg: string, _meta?: Record<string, unknown>) => {},
    }
    expect(() => logger.info('test', { key: 'value' })).not.toThrow()
  })
})

describe('consoleLogger', () => {
  beforeEach(() => {
    vi.spyOn(console, 'log').mockImplementation(() => {})
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.spyOn(console, 'debug').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('info logs to stdout', () => {
    consoleLogger.info('hello')
    expect(console.log).toHaveBeenCalledWith('[INFO] hello')
  })

  it('warn logs to stderr', () => {
    consoleLogger.warn('caution')
    expect(console.warn).toHaveBeenCalledWith('[WARN] caution')
  })

  it('error logs to stderr', () => {
    consoleLogger.error('fail')
    expect(console.error).toHaveBeenCalledWith('[ERROR] fail')
  })

  it('warn logs without meta (falsy branch)', () => {
    consoleLogger.warn('just warning')
    expect(console.warn).toHaveBeenCalledWith('[WARN] just warning')
  })

  it('error logs without meta (falsy branch)', () => {
    consoleLogger.error('just error')
    expect(console.error).toHaveBeenCalledWith('[ERROR] just error')
  })

  it('debug does not output when DEBUG is not set', () => {
    const originalEnv = process.env.DEBUG
    process.env.DEBUG = ''
    consoleLogger.debug('quiet')
    expect(console.debug).not.toHaveBeenCalled()
    process.env.DEBUG = originalEnv
  })

  it('debug outputs when DEBUG=1', () => {
    const originalEnv = process.env.DEBUG
    process.env.DEBUG = '1'
    consoleLogger.debug('verbose')
    expect(console.debug).toHaveBeenCalledWith('[DEBUG] verbose')
    process.env.DEBUG = originalEnv
  })

  it('includes meta in output when provided', () => {
    consoleLogger.info('test', { agentId: 'coding-agent' })
    expect(console.log).toHaveBeenCalledWith('[INFO] test {"agentId":"coding-agent"}')
  })

  it('logs warn with meta', () => {
    consoleLogger.warn('slow', { durationMs: 5000 })
    expect(console.warn).toHaveBeenCalledWith('[WARN] slow {"durationMs":5000}')
  })

  it('logs error with meta', () => {
    consoleLogger.error('fail', { code: 500 })
    expect(console.error).toHaveBeenCalledWith('[ERROR] fail {"code":500}')
  })

  it('debug with meta when DEBUG=1', () => {
    const originalEnv = process.env.DEBUG
    process.env.DEBUG = '1'
    consoleLogger.debug('detail', { key: 'val' })
    expect(console.debug).toHaveBeenCalledWith('[DEBUG] detail {"key":"val"}')
    process.env.DEBUG = originalEnv
  })
})
