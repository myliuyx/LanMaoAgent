# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**LanMaoAgent** — An AI agent platform that runs LLM-powered agents with tools (filesystem, git, terminal) in a CLI interface. Monorepo managed with pnpm workspaces.

## Development Commands

```sh
pnpm install                   # Install dependencies
pnpm run build                 # tsc --build + node build.mjs (esbuild bundles CLI)
pnpm run test                  # vitest run (all unit/contract/e2e tests, 80% coverage gate)
pnpm run lint                  # ESLint zero-warnings check
pnpm run format                # Prettier check
```

To run a single test: `pnpm run test -- <file-or-pattern>`
To watch tests: `./node_modules/.bin/vitest`

## Architecture Overview

### Package Dependency Graph (unidirectional, bottom-up)

```
shared-types (zero deps)
  ├── memory-stm (→ shared-types)
  ├── llm-adapter (→ shared-types)
  ├── tools/filesystem (→ shared-types)
  ├── tools/git      (→ shared-types)
  ├── tools/terminal (→ shared-types)
  ├── tool-core      (→ shared-types + memory-stm + llm-adapter)
  └── platform       (→ shared-types + llm-adapter + tool-core + memory-stm + all tools/*)
        └── apps/cli (→ platform)
```

No circular dependencies. Each package exports from `src/index.ts` directly (no compiled output at dev time).

### Key Interfaces (global contracts — breaking changes require updating all consumers)

- `ChatMessage`, `ToolCall`, `ToolResult`, `ToolDefinition` → `packages/shared-types/src/chat.ts`
- `ChatResponse`, `TokenUsage`, `AgentResult` → `packages/shared-types/src/llm.ts`
- `Agent`, `ToolHandler`, `ToolExecutionContext` → `packages/shared-types/src/agent.ts`
- `PlatformConfig` → `packages/shared-types/src/config.ts`

### Core Runtime Flow

1. **CLI** (`apps/cli/src/index.ts`) loads config from `~/.agent-platform/config.json`, builds agents, creates a `Platform` instance, and calls `platform.run(userInput)`.
2. **Platform** (`packages/platform/src/Platform.ts`) holds the LLM adapter, ToolRegistry, agent cache, and in-memory sessions. It requires an `"orchestrator"` agent in config.
3. **Agent Loop** (`packages/tool-core/src/runAgentLoop.ts`) iterates: call `llm.complete()` → execute tool calls via `ToolRegistry` → push results back to messages → compact STM if token budget exceeded → repeat (max 20 iterations).
4. **Session reuse**: Sessions keyed by `(agentId, projectRoot)` persist conversation history across `platform.run()` calls within the same process.

### Tool System

- `ToolHandler` interface: `id` + `getTools()` → `ToolDefinition[]` + `execute(call)` → `Promise<ToolResult>`
- Three built-in handlers: Filesystem, Git, Terminal (registered in Platform constructor)
- `DelegateToAgentHandler` (`packages/platform/src/tools/delegateTool.ts`) enables agent-to-agent delegation via the orchestrator
- Path safety enforced globally in `ToolRegistry.execute()`: extracts `path`/`filepath` from tool args and validates with `path.resolve` + `startsWith`

### LLM Adapter

- Supports Anthropic (Claude) and OpenAI-compatible providers (`packages/llm-adapter/src/ClaudeAdapter.ts`, `OpenAIAdapter.ts`)
- V1 signature: `complete(messages, tools?)` — messages array includes system prompt at index 0
- Retry on 429/502/503: up to 2 attempts with exponential backoff (1s → 2s)

### STM ShortTermMemory

- Ring buffer for message history. `compact()` uses rule-based role grouping (not LLM), has a `compacted` flag to prevent re-compaction.
- Token budget trigger: `contextWindow * compressionRatio` — when exceeded, compact frees messages and rebuilds STM.

### Configuration Loading Priority

1. `~/.agent-platform/config.json` (user config)
2. `ANTHROPIC_API_KEY` env var
3. Defaults from `DEFAULT_CONFIG` / `DEFAULT_LLM` in platform package

Empty arrays for `allowedPaths` and `terminalWhitelist` mean "use defaults" rather than "allow nothing".

### Testing

- Vitest config at root (`vitconfig.config.ts`) with resolve aliases mapping all `@agent-platform/*` packages to their `src/index.ts`
- Coverage targets: 80% across statements, branches, functions, lines
- Test directories: `tests/unit/`, `tests/contract-tests/`, `tests/e2e/`

### Build Output

- TypeScript compilation: `tsc --build` (project references) → `.js` + `.d.ts` alongside source
- CLI bundling: `node build.mjs` → `apps/cli/dist/cli.js` (esbuild, ESM, node20 target, externalizes node:* modules)
