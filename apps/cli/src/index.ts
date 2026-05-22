import os from 'node:os'
import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import readline from 'node:readline'
import type { AgentConfig, PlatformConfig } from '@agent-platform/platform'
import {
  DEFAULT_LLM,
  DEFAULT_CONFIG,
  BUILTIN_AGENTS,
  DEFAULT_AGENTS_DIR,
  DEFAULT_TOOLS,
  Platform,
} from '@agent-platform/platform'
import { theme } from './ui/theme.js'
import { Spinner } from './ui/spinner.js'
import { ToolView } from './ui/tool-view.js'
import { render } from './ui/renderer.js'
import { renderBanner } from './ui/theme.js'

function loadAgents(
  agentsDir: string,
  defaultTools: string[],
  readFileSync: typeof fs.readFileSync,
  builtinAgents: AgentConfig[],
): AgentConfig[] {
  const resolvedDir = agentsDir.startsWith('~')
    ? path.join(os.homedir(), agentsDir.slice(1))
    : agentsDir

  let index: string[]
  try {
    const parsed = JSON.parse(
      readFileSync(path.join(resolvedDir, 'index.json'), 'utf-8'),
    )
    if (!Array.isArray(parsed)) return builtinAgents
    index = parsed
  } catch {
    return builtinAgents
  }

  const builtinMap = new Map(builtinAgents.map((a) => [a.id, a]))
  const loaded = new Map<string, AgentConfig>()
  const result: AgentConfig[] = []

  function resolveOne(id: string, visited: Set<string>): AgentConfig {
    if (visited.has(id)) {
      throw new Error(`Circular extends detected for agent "${id}"`)
    }

    const cached = loaded.get(id)
    if (cached) return cached

    const agentPath = path.join(resolvedDir, id, 'agent.json')
    let fileCfg: Record<string, unknown>
    try {
      fileCfg = JSON.parse(readFileSync(agentPath, 'utf-8'))
    } catch {
      const builtin = builtinMap.get(id)
      if (!builtin) {
        throw new Error(
          `Agent "${id}" not found in agents dir or built-in`,
        )
      }
      loaded.set(id, builtin)
      return builtin
    }

    // Build nextVisited for recursive extends resolution
    const nextVisited = new Set(visited)
    nextVisited.add(id)

    const rawTools = (fileCfg.tools as string[]) ?? []
    const rawExtends = (fileCfg.extends as string) ?? ''
    const rawPrompt = (fileCfg.systemPrompt as string) ?? ''

    let mergedTools: string[]
    if (rawExtends) {
      const parent = resolveOne(rawExtends, nextVisited)
      mergedTools = [
        ...new Set([
          ...(parent.tools ?? defaultTools),
          ...rawTools,
        ]),
      ]
    } else if (rawTools.length > 0) {
      mergedTools = rawTools
    } else {
      mergedTools = [...defaultTools]
    }

    // Try reading system-prompt.md
    let systemPrompt = rawPrompt
    if (!systemPrompt) {
      const promptPath = path.join(resolvedDir, id, 'system-prompt.md')
      try {
        systemPrompt = readFileSync(promptPath, 'utf-8')
      } catch {
        const builtin = builtinMap.get(id)
        if (builtin) systemPrompt = builtin.systemPrompt
      }
    }

    const agent: AgentConfig = {
      id,
      name: (fileCfg.name as string) || id,
      description: (fileCfg.description as string) || '',
      systemPrompt,
      tools: mergedTools,
    }

    loaded.set(id, agent)
    return agent
  }

  for (const id of index) {
    result.push(resolveOne(id, new Set()))
  }

  return result
}

function loadConfig(
  readFileSync: typeof fs.readFileSync,
  proc: NodeJS.Process,
  userConfigOverride?: Partial<PlatformConfig>,
): PlatformConfig {
  let userConfig: Partial<PlatformConfig> = {}
  try {
    const CONFIG_FILE = path.join(
      os.homedir(),
      '.agent-platform',
      'config.json',
    )
    userConfig = JSON.parse(readFileSync(CONFIG_FILE, 'utf-8'))
  } catch {
    // config file missing or invalid — use defaults
  }

  if (userConfigOverride) {
    userConfig = { ...userConfig, ...userConfigOverride }
  }

  const envApiKey = proc.env.ANTHROPIC_API_KEY
  const llmApiKey = userConfig.llm?.apiKey ?? envApiKey

  const agentsDir = userConfig.agentsDir ?? DEFAULT_AGENTS_DIR
  const defaultTools = userConfig.defaultTools ?? DEFAULT_TOOLS
  const agents = loadAgents(
    agentsDir,
    defaultTools,
    readFileSync,
    BUILTIN_AGENTS,
  )

  return {
    llm: {
      ...DEFAULT_LLM,
      provider: 'anthropic',
      ...userConfig.llm,
      apiKey: llmApiKey,
    },
    agents,
    defaultTools,
    agentsDir,
    runtime: { ...DEFAULT_CONFIG.runtime, ...userConfig.runtime },
    security: { ...DEFAULT_CONFIG.security, ...userConfig.security },
    cli: {
      prompt:
        userConfig.cli?.prompt ??
        DEFAULT_CONFIG.cli?.prompt ??
        'Ask me anything: ',
    },
  }
}

export function runCli(
  deps: {
    readFileSync?: typeof fs.readFileSync
    process?: NodeJS.Process
    console?: Console
    PlatformCtor?: typeof Platform
    readline?: typeof readline
    userConfigOverride?: Partial<PlatformConfig>
  } = {},
): { abortController: AbortController } {
  const proc = deps.process ?? process
  const cons = deps.console ?? console
  const readFileSync = deps.readFileSync ?? fs.readFileSync
  const PlatformCtor = deps.PlatformCtor ?? Platform
  const rlMod = deps.readline ?? readline

  const config = loadConfig(readFileSync, proc, deps.userConfigOverride)

  const abortController = new AbortController()
  let pendingQueue: string[] = []
  let running = false

  proc.on('SIGINT', () => {
    spinner.stop()
    abortController.abort()
    pendingQueue = []
    cons.log('\nExiting...')
    proc.exit(0)
  })

  const platform = new PlatformCtor(config)

  const toolView = new ToolView()
  const spinner = new Spinner()

  const promptText = theme.prompt('> ') + (config.cli?.prompt ?? 'Ask me anything: ')
  const rl = rlMod.createInterface({
    input: proc.stdin,
    output: proc.stdout,
    prompt: promptText,
  })

  // ESC 取消排队（仅 TTY 环境）
  if (proc.stdin.isTTY) {
    readline.emitKeypressEvents(proc.stdin)
    proc.stdin.setRawMode(true)

    proc.stdin.on('keypress', (_str: string, key: { name?: string }) => {
      if (key?.name === 'escape' && pendingQueue.length > 0) {
        pendingQueue = []
        cons.log('\n' + theme.cancel('[排队已取消]'))
        rl.prompt()
      }
    })
  }

  // Banner on startup
  cons.log(renderBanner())
  cons.log(theme.separator('─'.repeat(65)))

  rl.prompt()

  async function processInput(input: string) {
    const sanitizedInput = input.trim()
    if (!sanitizedInput) {
      rl.prompt()
      return
    }

    try {
      running = true
      spinner.start('思考中...')
      let streamedAny = false
      const result = await platform.run(
        sanitizedInput,
        abortController.signal,
        (chunk) => {
          if (!streamedAny) spinner.stop()
          streamedAny = true
          proc.stdout.write(chunk)
        },
        (call, agentId) => {
          spinner.stop()
          toolView.onStart(call, agentId)
        },
        (call, res, agentId) => {
          toolView.onFinish(call, res, agentId)
        },
      )

      spinner.stop()

      if (result.status === 'aborted') {
        return
      }

      if (streamedAny) {
        proc.stdout.write('\n')
      } else if (result.output) {
        cons.log(render(result.output))
      } else {
        const msg =
          result.status === 'failed'
            ? theme.error(`[LLM temporarily unavailable: ${result.error}] Retry by re-entering your request.`)
            : theme.error(`Error: ${result.error ?? `[${result.status}] No error message provided`}`)
        cons.error(msg)
      }
    } catch (e) {
      spinner.stop()
      if ((e as Error).name === 'AbortError') return
      cons.error(theme.error(`Platform error: ${(e as Error).message}`))
    } finally {
      running = false
      if (pendingQueue.length > 0) {
        const next = pendingQueue.shift()!
        processInput(next).catch(() => {})
      } else {
        rl.prompt()
      }
    }
  }

  rl.on('line', (input: string) => {
    const sanitizedInput = input.trim()
    if (!sanitizedInput) {
      rl.prompt()
      return
    }

    if (running) {
      pendingQueue.push(sanitizedInput)
      cons.log(theme.queue(`⏳ 任务已排队 (${pendingQueue.length} 个待处理). 按 ESC 取消排队`))
      rl.prompt()
      return
    }

    processInput(input).catch(() => {})
  })

  // 退出时恢复 raw mode
  proc.on('exit', () => {
    spinner.stop()
    if (proc.stdin.isTTY) {
      proc.stdin.setRawMode(false)
    }
  })

  return { abortController }
}

const isMain = process.argv[1] === fileURLToPath(import.meta.url)
if (isMain) {
  runCli()
}
