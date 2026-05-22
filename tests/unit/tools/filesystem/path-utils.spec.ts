import { describe, it, expect } from 'vitest'
import { resolve } from 'node:path'

// These are internal utilities, imported directly from source.
// The vitest alias @agent-platform/tools-filesystem points to
// packages/tools/filesystem/src/index.ts which re-exports from FilesystemHandler.
// We import pathUtils directly since it's not part of the public API.
import {
  isInAllowedPath,
  validateAncestors,
  safeResolve,
} from '../../../../packages/tools/filesystem/src/pathUtils.js'

describe('isInAllowedPath', () => {
  it('returns true when target equals allowed path', () => {
    expect(isInAllowedPath('/workspace', ['/workspace'])).toBe(true)
  })

  it('returns true when target is inside allowed path', () => {
    expect(isInAllowedPath('/workspace/src', ['/workspace'])).toBe(true)
  })

  it('returns true for deeply nested path', () => {
    expect(isInAllowedPath('/workspace/a/b/c/d', ['/workspace'])).toBe(true)
  })

  it('returns false for path outside allowed', () => {
    expect(isInAllowedPath('/other', ['/workspace'])).toBe(false)
  })

  it('prevents prefix attack (/workspace-evil)', () => {
    expect(isInAllowedPath('/workspace-evil', ['/workspace'])).toBe(false)
  })

  it('returns true when target matches any of multiple allowed paths', () => {
    expect(isInAllowedPath('/project-b/file', ['/project-a', '/project-b'])).toBe(true)
  })

  it('returns false when target matches none of multiple allowed paths', () => {
    expect(isInAllowedPath('/project-c/file', ['/project-a', '/project-b'])).toBe(false)
  })

  it('handles empty allowed paths list', () => {
    expect(isInAllowedPath('/workspace', [])).toBe(false)
  })

  it('matches exact path with trailing slash equivalent', () => {
    expect(isInAllowedPath('/workspace', ['/workspace'])).toBe(true)
  })
})

describe('validateAncestors', () => {
  it('returns true for direct child of allowed path', () => {
    expect(validateAncestors('/workspace/subdir', ['/workspace'])).toBe(true)
  })

  it('returns true for deeply nested path under allowed root', () => {
    expect(validateAncestors('/workspace/a/b/c', ['/workspace'])).toBe(true)
  })

  it('returns false when parent is outside allowed', () => {
    expect(validateAncestors('/outside/subdir', ['/workspace'])).toBe(false)
  })

  it('returns false for deeply nested outside path', () => {
    expect(validateAncestors('/outside/a/b/c', ['/workspace'])).toBe(false)
  })

  it('handles path within second allowed path', () => {
    expect(validateAncestors('/project-b/subdir', ['/project-a', '/project-b'])).toBe(true)
  })

  it('handles empty allowed paths', () => {
    expect(validateAncestors('/workspace/subdir', [])).toBe(false)
  })
})

describe('safeResolve', () => {
  it('resolves relative paths', () => {
    const result = safeResolve('.')
    expect(result).toBe(resolve('.'))
  })

  it('resolves absolute paths without change (for existing paths)', () => {
    const result = safeResolve('/tmp')
    expect(result).toBe(resolve('/tmp'))
  })
})
