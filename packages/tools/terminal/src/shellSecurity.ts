/** Truly dangerous shell metacharacters that enable command injection.
 * These are rejected regardless of the command being run. */
const DANGEROUS_METACHARACTERS = /[;`]|\$\(|\$\{|!`|&&|\|\||>>/

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
