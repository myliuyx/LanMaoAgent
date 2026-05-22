import {
  lstat,
  readFile,
  readdir,
  writeFile,
} from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'
import {
  safeResolve,
  isInAllowedPath,
  validateAncestors,
  MAX_STRING_ARG_LENGTH,
  GREP_MAX_RESULTS,
} from './pathUtils.js'
import type {
  Logger,
  ToolHandler,
  ToolDefinition,
  ToolCall,
  ToolResult,
  ToolExecutionContext,
} from '@agent-platform/shared-types'
import { consoleLogger } from '@agent-platform/shared-types'

function validateStringArg(
  value: unknown,
  name: string,
): string | null {
  if (value === undefined || value === null) {
    return `${name} is required`
  }
  if (typeof value !== 'string') {
    return `${name} must be a string`
  }
  const trimmed = value.trim()
  if (trimmed.length === 0) {
    return `${name} cannot be empty`
  }
  if (value.length > MAX_STRING_ARG_LENGTH) {
    return `${name} exceeds maximum length of ${MAX_STRING_ARG_LENGTH} characters. Split into multiple files or truncate.`
  }
  return null
}

function validateContentArg(value: unknown): string | null {
  const err = validateStringArg(value, 'content')
  if (err === `content exceeds maximum length of ${MAX_STRING_ARG_LENGTH} characters`) {
    return `${err} Use multiple write_file calls for large files.`
  }
  return err
}

const SCHEMA_PATH: Record<string, unknown> = {
  type: 'object',
  properties: {
    path: { type: 'string', description: 'File or directory path' },
  },
  required: ['path'],
}

const SCHEMA_GREP: Record<string, unknown> = {
  type: 'object',
  properties: {
    pattern: { type: 'string', description: 'Regular expression pattern' },
    path: { type: 'string', description: 'File path' },
  },
  required: ['pattern', 'path'],
}

const SCHEMA_GREP_R: Record<string, unknown> = {
  type: 'object',
  properties: {
    pattern: { type: 'string', description: 'Regular expression pattern' },
    path: { type: 'string', description: 'Root directory to search' },
  },
  required: ['pattern', 'path'],
}

const SCHEMA_WRITE: Record<string, unknown> = {
  type: 'object',
  properties: {
    path: { type: 'string', description: 'File path to write' },
    content: { type: 'string', description: 'Content to write. For large files exceeding ~64KB, split into multiple calls using append mode.' },
    append: { type: 'boolean', description: 'If true, append content instead of overwriting the file. Use this for writing large files in chunks.' },
  },
  required: ['path', 'content'],
}

const SCHEMA_EDIT: Record<string, unknown> = {
  type: 'object',
  properties: {
    path: { type: 'string', description: 'File path to edit' },
    old_string: { type: 'string', description: 'Text to replace' },
    new_string: { type: 'string', description: 'Replacement text' },
    regex: {
      type: 'boolean',
      description: 'If true, treat old_string as a regular expression',
    },
  },
  required: ['path', 'old_string', 'new_string'],
}

export class FilesystemHandler implements ToolHandler {
  readonly id = 'filesystem'
  private allowedPaths: string[]
  private logger: Logger

  constructor(allowedPaths?: string[], logger?: Logger) {
    this.allowedPaths = allowedPaths && allowedPaths.length > 0 ? allowedPaths : [process.cwd()]
    this.logger = logger ?? consoleLogger
  }

  /**
   * Validates that a path is within the allowed paths.
   * Uses realpathSync to resolve symlinks on every call (prevents TOCTOU attacks).
   * For write operations, recursively checks each ancestor directory via validateAncestors.
   */
  private validatePath(
    path: string,
    allowedPaths?: string[],
    isWriteOperation = false,
  ): ToolResult | null {
    const checkAllowed = (targetPath: string): boolean => {
      const realTarget = safeResolve(targetPath)
      if (realTarget === null) return false
      const pathsToCheck = allowedPaths || this.allowedPaths
      return isInAllowedPath(realTarget, pathsToCheck)
    }

    try {
      // For write operations on non-existent files, validate all ancestor directories.
      if (isWriteOperation && !existsSync(resolve(path))) {
        if (!validateAncestors(path, allowedPaths || this.allowedPaths)) {
          return { content: `Access denied: path '${path}' is outside allowed directories`, isError: true, retryable: false }
        }
        // Also check the target itself in case it's an existing directory
        if (existsSync(resolve(path)) && !checkAllowed(path)) {
          return { content: `Access denied: path '${path}' is outside allowed directories`, isError: true, retryable: false }
        }
      }

      if (!checkAllowed(path)) {
        return { content: `Access denied: path '${path}' is outside allowed directories`, isError: true, retryable: false }
      }
    } catch {
      return { content: `Access denied: invalid path '${path}'`, isError: true, retryable: false }
    }

    return null // valid
  }

  getTools(): ToolDefinition[] {
    return [
      {
        name: 'read_file',
        description: 'Read the contents of a file',
        parameters: SCHEMA_PATH,
      },
      {
        name: 'list_dir',
        description: 'List files and directories in a directory',
        parameters: SCHEMA_PATH,
      },
      {
        name: 'grep',
        description: 'Search for a regex pattern in a single file',
        parameters: SCHEMA_GREP,
      },
      {
        name: 'grep_r',
        description: 'Recursively search for a regex pattern in a directory tree',
        parameters: SCHEMA_GREP_R,
      },
      {
        name: 'write_file',
        description: 'Write content to a file (creates or overwrites)',
        parameters: SCHEMA_WRITE,
      },
      {
        name: 'edit_file',
        description: 'Edit a file by replacing text (literal or regex)',
        parameters: SCHEMA_EDIT,
      },
    ]
  }

  async execute(call: ToolCall, _ctx: ToolExecutionContext): Promise<ToolResult> {
    const args = call.arguments as Record<string, unknown>

    try {
      switch (call.name) {
        case 'read_file': {
          const pathErr = validateStringArg(args['path'], 'path')
          if (pathErr) return { content: pathErr, isError: true, retryable: false }
          const pathVal = args['path'] as string
          const pathCheck = this.validatePath(pathVal)
          if (pathCheck) return pathCheck
          return this.readFile(pathVal)
        }
        case 'list_dir': {
          const pathErr = validateStringArg(args['path'], 'path')
          if (pathErr) return { content: pathErr, isError: true, retryable: false }
          const pathVal = args['path'] as string
          const pathCheck = this.validatePath(pathVal)
          if (pathCheck) return pathCheck
          return this.listDir(pathVal)
        }
        case 'grep': {
          const patternErr = validateStringArg(args['pattern'], 'pattern')
          if (patternErr) return { content: patternErr, isError: true, retryable: false }
          const pathErr = validateStringArg(args['path'], 'path')
          if (pathErr) return { content: pathErr, isError: true, retryable: false }
          const patternVal = args['pattern'] as string
          const pathVal = args['path'] as string
          const pathCheck = this.validatePath(pathVal)
          if (pathCheck) return pathCheck
          return this.grep(patternVal, pathVal)
        }
        case 'grep_r': {
          const patternErr = validateStringArg(args['pattern'], 'pattern')
          if (patternErr) return { content: patternErr, isError: true, retryable: false }
          const pathErr = validateStringArg(args['path'], 'path')
          if (pathErr) return { content: pathErr, isError: true, retryable: false }
          const patternVal = args['pattern'] as string
          const pathVal = args['path'] as string
          const pathCheck = this.validatePath(pathVal)
          if (pathCheck) return pathCheck
          return this.grepR(patternVal, pathVal)
        }
        case 'write_file': {
          const pathErr = validateStringArg(args['path'], 'path')
          if (pathErr) return { content: pathErr, isError: true, retryable: false }
          const contentErr = validateContentArg(args['content'])
          if (contentErr) return { content: contentErr, isError: true, retryable: false }
          const pathVal = args['path'] as string
          const contentVal = args['content'] as string
          const append = typeof args['append'] === 'boolean' ? (args['append'] as boolean) : undefined
          const pathCheck = this.validatePath(pathVal, undefined, true)
          if (pathCheck) return pathCheck
          return this.writeFile(pathVal, contentVal, append)
        }
        case 'edit_file': {
          const pathErr = validateStringArg(args['path'], 'path')
          if (pathErr) return { content: pathErr, isError: true, retryable: false }
          const oldStrErr = validateStringArg(args['old_string'], 'old_string')
          if (oldStrErr) return { content: oldStrErr, isError: true, retryable: false }
          const newStrErr = validateStringArg(args['new_string'], 'new_string')
          if (newStrErr) return { content: newStrErr, isError: true, retryable: false }
          const pathVal = args['path'] as string
          const oldStrVal = args['old_string'] as string
          const newStrVal = args['new_string'] as string
          const useRegex = typeof args['regex'] === 'boolean' ? (args['regex'] as boolean) : undefined
          const pathCheck = this.validatePath(pathVal, undefined, true)
          if (pathCheck) return pathCheck
          return this.editFile(pathVal, oldStrVal, newStrVal, useRegex)
        }
        default:
          return { content: `Unknown tool: ${call.name}`, isError: true, retryable: false }
      }
    } catch {
      this.logger.error('Internal error in tool execution', { tool: call.name })
      return { content: 'Internal error occurred', isError: true, retryable: false }
    }
  }

  private async readFile(path: string): Promise<ToolResult> {
    try {
      const content = await readFile(path, 'utf-8')
      return { content, isError: false }
    } catch (e) {
      const nodeErr = e as NodeJS.ErrnoException
      if (nodeErr.code === 'ENOENT') {
        return {
          content: `ENOENT: no such file or directory '${path}'`,
          isError: true,
          retryable: false,
        }
      }
      throw e
    }
  }

  private async listDir(path: string): Promise<ToolResult> {
    try {
      const entries = await readdir(path, { withFileTypes: true })
      const result = entries.map((e) => ({
        name: e.name,
        type: e.isDirectory() ? 'directory' as const : 'file' as const,
      }))
      return { content: JSON.stringify(result), isError: false }
    } catch (e) {
      const nodeErr = e as NodeJS.ErrnoException
      if (nodeErr.code === 'ENOENT') {
        return {
          content: `ENOENT: no such file or directory '${path}'`,
          isError: true,
          retryable: false,
        }
      }
      throw e
    }
  }

  private async grep(pattern: string, filePath: string): Promise<ToolResult> {
    let regex: RegExp
    try {
      regex = new RegExp(pattern)
    } catch {
      return { content: `Invalid regex pattern: ${pattern}`, isError: true, retryable: false }
    }
    const content = await readFile(filePath, 'utf-8')
    const lines = content.split('\n')
    const matches: Array<{ line: number; content: string }> = []
    for (let i = 0; i < lines.length && matches.length < GREP_MAX_RESULTS; i++) {
      if (regex.test(lines[i])) {
        regex.lastIndex = 0
        matches.push({ line: i + 1, content: lines[i] })
      } else {
        regex.lastIndex = 0
      }
    }

    let json: string
    try {
      json = JSON.stringify(matches)
    } catch {
      return { content: 'Failed to serialize results', isError: true, retryable: false }
    }
    return { content: json, isError: false }
  }

  private async grepR(pattern: string, rootPath: string): Promise<ToolResult> {
    if (!existsSync(rootPath)) {
      return {
        content: `ENOENT: no such file or directory '${rootPath}'`,
        isError: true,
        retryable: false,
      }
    }
    let regex: RegExp
    try {
      regex = new RegExp(pattern)
    } catch {
      return { content: `Invalid regex pattern: ${pattern}`, isError: true, retryable: false }
    }
    const results: Array<{
      file: string
      line: number
      content: string
    }> = []
    const MAX_DEPTH = 50
    let wasTruncated = false
    const walk = async (dir: string, depth: number): Promise<void> => {
      if (depth > MAX_DEPTH) return
      let entries: string[]
      try {
        entries = await readdir(dir)
      } catch {
        return
      }
      for (const entry of entries) {
        if (results.length >= GREP_MAX_RESULTS) {
          wasTruncated = true
          return
        }
        const fullPath = join(dir, entry)
        let entryStat: import('node:fs').Stats
        try {
          entryStat = await lstat(fullPath)
        } catch {
          continue
        }
        if (entryStat.isSymbolicLink()) {
          continue
        }
        if (entryStat.isDirectory()) {
          await walk(fullPath, depth + 1)
        } else if (entryStat.isFile()) {
          try {
            const fileContent = await readFile(fullPath, 'utf-8')
            const lines = fileContent.split('\n')
            for (let i = 0; i < lines.length && results.length < GREP_MAX_RESULTS; i++) {
              if (regex.test(lines[i])) {
                regex.lastIndex = 0
                results.push({
                  file: relative(rootPath, fullPath),
                  line: i + 1,
                  content: lines[i],
                })
              } else {
                regex.lastIndex = 0
              }
            }
          } catch {
            // skip unreadable files
          }
        }
      }
    }
    await walk(rootPath, 0)

    let json: string
    try {
      json = JSON.stringify(results)
    } catch {
      return { content: 'Failed to serialize results', isError: true, retryable: false }
    }

    let finalContent: string
    const metadata: Record<string, unknown> | undefined = wasTruncated
      ? { truncated: true, maxResults: GREP_MAX_RESULTS }
      : undefined

    if (wasTruncated) {
      finalContent = json + '\n[truncated]'
    } else {
      finalContent = json
    }

    return { content: finalContent, isError: false, metadata }
  }

  private async writeFile(
    path: string,
    content: string,
    append?: boolean,
  ): Promise<ToolResult> {
    const flag = append ? 'a' : 'w'
    await writeFile(path, content, { encoding: 'utf-8', flag })
    return { content: `File ${append ? 'appended to' : 'written'} successfully`, isError: false }
  }

  private async editFile(
    path: string,
    oldString: string,
    newString: string,
    useRegex: boolean | undefined,
  ): Promise<ToolResult> {
    // When useRegex is false and multiple matches exist, only the first occurrence is replaced.
    // When useRegex is true or there's exactly one match, all occurrences are replaced via split+join.
    const fileContent = await readFile(path, 'utf-8')

    if (useRegex) {
      let regex: RegExp
      try {
        regex = new RegExp(oldString)
      } catch {
        return {
          content: `Invalid regex pattern: ${oldString}`,
          isError: true,
          retryable: false,
        }
      }
      if (!regex.test(fileContent)) {
        return {
          content: 'No match found for regex',
          isError: true,
          retryable: false,
        }
      }
      const updated = fileContent.replace(regex, newString)
      await writeFile(path, updated, 'utf-8')
      return { content: 'File edited successfully', isError: false }
    }

    if (!fileContent.includes(oldString)) {
      return {
        content: `old_string not found: '${oldString}'`,
        isError: true,
        retryable: false,
      }
    }

    const allMatches = fileContent.split(oldString)
    let updated: string
    if (allMatches.length > 2 && !useRegex) {
      // Multiple matches in non-regex mode — only replace the first occurrence.
      const idx = fileContent.indexOf(oldString)
      updated = fileContent.substring(0, idx) + newString + fileContent.substring(idx + oldString.length)
    } else {
      updated = fileContent.split(oldString).join(newString)
    }

    await writeFile(path, updated, 'utf-8')
    const matchCount = allMatches.length - 1
    return { content: matchCount > 1 && !useRegex ? `File edited (1 of ${matchCount} matches replaced)` : 'File edited successfully', isError: false }
  }
}
