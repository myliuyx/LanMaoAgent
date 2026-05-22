import { existsSync, realpathSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'

// ── Constants ────────────────────────────────────────────────
export const MAX_STRING_ARG_LENGTH = 64 * 1024 // 64KB max per write_file call — Claude sonnet can output at most ~8K tokens (~20-40KB text), so this covers any single LLM call. For larger files, use append mode.
export const GREP_MAX_RESULTS = 200
export const OUTPUT_TRUNCATE_THRESHOLD = 10 * 1024
export const EXEC_TIMEOUT_MS = 30_000
export const EXEC_MAX_BUFFER = 20 * 1024

// ── Path resolution ─────────────────────────────────────────

/**
 * Resolve a path safely: resolve + realpathSync (if file exists).
 * If the file doesn't exist, walks up to find the nearest existing parent
 * directory and resolves that via realpathSync, then appends the remaining
 * relative portion. This prevents symlink-based TOCTOU attacks where an
 * attacker replaces a parent directory with a symlink between checks.
 */
export function safeResolve(targetPath: string): string | null {
  const resolved = resolve(targetPath)

  try {
    // Case 1: file exists — return its real path directly
    if (existsSync(resolved)) {
      return realpathSync(resolved)
    }

    // Case 2: file does not exist — walk up the directory tree to find
    // the nearest existing parent, resolve that via realpathSync, then
    // append the remaining relative portion of the original path.
    let current = resolved
    while (current !== '/' && !existsSync(current)) {
      current = dirname(current)
    }

    if (current === '/') {
      // Edge case: nothing exists up to root — return resolved as-is
      return resolved
    }

    const realParent = realpathSync(current)
    const relativePath = resolved.slice(current.length)
    return join(realParent, relativePath)
  } catch (e) {
    console.warn(`[safeResolve] Failed to resolve path "${targetPath}": ${e instanceof Error ? e.message : 'unknown error'}`)
    return null
  }
}

// ── Access control ──────────────────────────────────────────

/**
 * Check if a real path is within any of the allowed paths.
 * Uses strict prefix matching with '/' separator to prevent path prefix attacks:
 *   - "/workspace" matches "/workspace/file" but NOT "/workspace-evil/file"
 */
export function isInAllowedPath(realTarget: string, allowedPaths: string[]): boolean {
  // Normalize trailing slashes so "/workspace" and "/workspace/" are treated identically
  const normalizedTarget = realTarget.replace(/\/+$/, '')
  for (const p of allowedPaths) {
    const resolvedAllowed = safeResolve(resolve(p))
    if (resolvedAllowed === null) continue // skip paths that can't be resolved
    const normalizedAllowed = resolvedAllowed.replace(/\/+$/, '')
    if (normalizedTarget === normalizedAllowed || normalizedTarget.startsWith(normalizedAllowed + '/')) {
      return true
    }
  }
  return false
}

/**
 * Check that the resolved parent directory is within allowed paths.
 */
export function validateAncestors(targetPath: string, allowedPaths: string[]): boolean {
  const resolved = safeResolve(resolve(targetPath))
  if (resolved === null) return false
  const current = dirname(resolved)
  return isInAllowedPath(current, allowedPaths)
}
