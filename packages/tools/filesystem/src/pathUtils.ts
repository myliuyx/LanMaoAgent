import { existsSync, realpathSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

// ── Constants ────────────────────────────────────────────────
export const MAX_STRING_ARG_LENGTH = 4096
export const GREP_MAX_RESULTS = 200
export const OUTPUT_TRUNCATE_THRESHOLD = 10 * 1024
export const EXEC_TIMEOUT_MS = 30_000
export const EXEC_MAX_BUFFER = 20 * 1024

// ── Path resolution ─────────────────────────────────────────

/**
 * Resolve a path safely: resolve + realpathSync (if file exists).
 * Falls back to resolved path if the file doesn't exist.
 */
export function safeResolve(targetPath: string): string {
  const resolved = resolve(targetPath)
  try {
    return existsSync(resolved) ? realpathSync(resolved) : resolved
  } catch {
    return resolved
  }
}

// ── Access control ──────────────────────────────────────────

/**
 * Check if a real path is within any of the allowed paths.
 * Uses strict prefix matching with '/' separator to prevent path prefix attacks:
 *   - "/workspace" matches "/workspace/file" but NOT "/workspace-evil/file"
 */
export function isInAllowedPath(realTarget: string, allowedPaths: string[]): boolean {
  const resolvedAllowed = allowedPaths.map(p => safeResolve(resolve(p)))
  for (const allowed of resolvedAllowed) {
    if (realTarget === allowed || realTarget.startsWith(allowed + '/')) {
      return true
    }
  }
  return false
}

/**
 * Check that every ancestor directory up to root is within allowed paths.
 * Walks from target's parent up to filesystem root, resolving symlinks at each step.
 */
export function validateAncestors(targetPath: string, allowedPaths: string[]): boolean {
  let current = dirname(safeResolve(resolve(targetPath)))
  const root = resolve('/')

  while (current !== root) {
    if (!isInAllowedPath(current, allowedPaths)) return false
    const parent = dirname(current)
    if (parent === current) break // reached filesystem root
    current = parent
  }
  return true
}
