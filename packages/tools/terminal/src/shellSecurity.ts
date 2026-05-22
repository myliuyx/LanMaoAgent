/**
 * Dangerous shell metacharacters blocked regardless of command.
 *
 * 安全模型说明:
 * - execFile() 不经过 shell，所以 &&, ||, >>, | 等 shell 元字符只是普通参数，无注入风险
 * - 主要防线是 whitelist（仅允许信任的命令），其次是此正则检测
 * - 此正则只拦截真正危险的注入：; ` $() ${} — 这些即使在 execFile 的 argv 中
 *   也可能通过某些命令的内部处理（如 sh -c、eval）被利用
 */
const DANGEROUS_METACHARACTERS = /[;`]|\$\(|\${.*}/

/** Dangerous patterns that should always be blocked (e.g. rm -rf). */
const ALWAYS_DANGEROUS_PATTERNS: Array<{ pattern: RegExp; reason: string }> = [
  { pattern: /^rm\s+(-rf|-fr)/, reason: 'recursive force deletion is not allowed' },
  { pattern: /^chmod\s+(0\d{3}|777|666|444|222|111)\b/, reason: 'overly permissive chmod modes are not allowed' },
  { pattern: /^\s*(dd|mkfs|fdisk)/, reason: 'disk operations are not allowed' },
  { pattern: /^(\.\.\/|\.\.\\)/, reason: 'parent directory traversal is not allowed' },
]

export function checkShellInjection(command: string): { blocked: true; reason: string } | null {
  // Block truly dangerous injection characters regardless of command
  if (DANGEROUS_METACHARACTERS.test(command)) {
    return { blocked: true, reason: 'Potential injection detected' }
  }

  for (const { pattern, reason } of ALWAYS_DANGEROUS_PATTERNS) {
    if (pattern.test(command)) {
      return { blocked: true, reason: `Blocked: ${reason}` }
    }
  }

  return null
}
