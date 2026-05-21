import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { FilesystemHandler } from '@agent-platform/tools-filesystem'
import {
  existsSync,
  mkdtempSync,
  writeFileSync,
  mkdirSync,
  rmSync,
} from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import type { ToolExecutionContext } from '@agent-platform/shared-types'

function tmpDir(): string {
  const dir = mkdtempSync(join(tmpdir(), 'fs-handler-test-'))
  return dir
}

function ctx(cwd: string): ToolExecutionContext {
  return { sessionId: 'test', agentId: 'test', cwd }
}

describe('FilesystemHandler', () => {
  // Allow operations in /tmp where test temp directories live.
  const handler = new FilesystemHandler(['/tmp'])
  let dir: string

  beforeEach(() => {
    dir = tmpDir()
  })

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true })
  })

  describe('getTools', () => {
    it('returns 6 tool definitions', () => {
      const tools = handler.getTools()
      expect(tools).toHaveLength(6)
      const names = tools.map((t) => t.name)
      expect(names).toContain('read_file')
      expect(names).toContain('list_dir')
      expect(names).toContain('grep')
      expect(names).toContain('grep_r')
      expect(names).toContain('write_file')
      expect(names).toContain('edit_file')
    })
  })

  describe('read_file', () => {
    it('returns file content as UTF-8 string', async () => {
      const filePath = join(dir, 'test.txt')
      writeFileSync(filePath, 'hello world', 'utf-8')
      const result = await handler.execute(
        { id: '1', name: 'read_file', arguments: { path: filePath } },
        ctx(dir),
      )
      expect(result.isError).toBeFalsy()
      expect(result.content).toBe('hello world')
    })

    it('for non-existent path returns isError: true', async () => {
      const result = await handler.execute(
        {
          id: '1',
          name: 'read_file',
          arguments: { path: join(dir, 'nope.txt') },
        },
        ctx(dir),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('ENOENT')
    })
  })

  describe('list_dir', () => {
    it('returns files and directories with correct types', async () => {
      writeFileSync(join(dir, 'a.txt'), 'a', 'utf-8')
      mkdirSync(join(dir, 'sub'))
      const result = await handler.execute(
        { id: '1', name: 'list_dir', arguments: { path: dir } },
        ctx(dir),
      )
      expect(result.isError).toBeFalsy()
      const entries = JSON.parse(result.content) as Array<{
        name: string
        type: string
      }>
      const fileNames = entries.map((e) => e.name).sort()
      expect(fileNames).toEqual(['a.txt', 'sub'])
      const aTxt = entries.find((e) => e.name === 'a.txt')!
      expect(aTxt.type).toBe('file')
      const sub = entries.find((e) => e.name === 'sub')!
      expect(sub.type).toBe('directory')
    })

    it('returns isError for non-existent directory', async () => {
      const result = await handler.execute(
        {
          id: '1',
          name: 'list_dir',
          arguments: { path: join(dir, 'nonexistent') },
        },
        ctx(dir),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('ENOENT')
    })
  })

  describe('grep', () => {
    it('finds matching lines with line numbers in single file', async () => {
      const filePath = join(dir, 'test.txt')
      writeFileSync(filePath, 'foo\nbar\nbaz\nfoo\n', 'utf-8')
      const result = await handler.execute(
        {
          id: '1',
          name: 'grep',
          arguments: { pattern: 'foo', path: filePath },
        },
        ctx(dir),
      )
      expect(result.isError).toBeFalsy()
      const matches = JSON.parse(result.content) as Array<{
        line: number
        content: string
      }>
      expect(matches).toHaveLength(2)
      expect(matches[0].line).toBe(1)
      expect(matches[0].content).toBe('foo')
      expect(matches[1].line).toBe(4)
    })

    it('returns empty array when no matches', async () => {
      const filePath = join(dir, 'test.txt')
      writeFileSync(filePath, 'abc\ndef\n', 'utf-8')
      const result = await handler.execute(
        {
          id: '1',
          name: 'grep',
          arguments: { pattern: 'xyz', path: filePath },
        },
        ctx(dir),
      )
      expect(result.isError).toBeFalsy()
      expect(JSON.parse(result.content)).toEqual([])
    })

    it('returns isError for invalid regex pattern', async () => {
      const filePath = join(dir, 'test.txt')
      writeFileSync(filePath, 'abc', 'utf-8')
      const result = await handler.execute(
        {
          id: '1',
          name: 'grep',
          arguments: { pattern: '[invalid', path: filePath },
        },
        ctx(dir),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('Invalid regex')
    })
  })

  describe('grep_r', () => {
    it('searches recursively across subdirectories', async () => {
      writeFileSync(join(dir, 'a.ts'), 'const x = 1\n', 'utf-8')
      mkdirSync(join(dir, 'nested'))
      writeFileSync(join(dir, 'nested', 'b.js'), 'const x = 2\n', 'utf-8')
      writeFileSync(join(dir, 'nested', 'c.txt'), 'const x = 3\n', 'utf-8')
      const result = await handler.execute(
        {
          id: '1',
          name: 'grep_r',
          arguments: { pattern: 'const x', path: dir },
        },
        ctx(dir),
      )
      expect(result.isError).toBeFalsy()
      const matches = JSON.parse(result.content) as Array<{
        file: string
        line: number
        content: string
      }>
      // Now searches all files (not just code extensions)
      expect(matches).toHaveLength(3)
    })

    it('truncates at 200 results with marker', async () => {
      // Create a dir with many matching lines across many files
      const manyDir = join(dir, 'many')
      mkdirSync(manyDir)
      for (let i = 0; i < 30; i++) {
        writeFileSync(join(manyDir, `f${i}.ts`), 'match\n'.repeat(10), 'utf-8')
      }
      const result = await handler.execute(
        {
          id: '1',
          name: 'grep_r',
          arguments: { pattern: 'match', path: manyDir },
        },
        ctx(manyDir),
      )
      expect(result.isError).toBeFalsy()
      const [jsonPart, marker] = result.content.split('\n')
      const matches = JSON.parse(jsonPart) as Array<unknown>
      expect(matches).toHaveLength(200)
      expect(marker).toBe('[truncated]')
    })

    it('non-existent dir returns isError', async () => {
      const result = await handler.execute(
        {
          id: '1',
          name: 'grep_r',
          arguments: { pattern: 'x', path: join(dir, 'missing') },
        },
        ctx(dir),
      )
      expect(result.isError).toBe(true)
    })

    it('returns isError for invalid regex pattern', async () => {
      const result = await handler.execute(
        {
          id: '1',
          name: 'grep_r',
          arguments: { pattern: '[invalid', path: dir },
        },
        ctx(dir),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('Invalid regex')
    })
  })

  describe('write_file', () => {
    it('creates new file with correct content', async () => {
      const filePath = join(dir, 'new.txt')
      const result = await handler.execute(
        {
          id: '1',
          name: 'write_file',
          arguments: { path: filePath, content: 'hello' },
        },
        ctx(dir),
      )
      expect(result.isError).toBeFalsy()
      expect(existsSync(filePath)).toBe(true)
      const content = await import('node:fs').then((fs) =>
        fs.readFileSync(filePath, 'utf-8'),
      )
      expect(content).toBe('hello')
    })

    it('overwrites existing file (not append)', async () => {
      const filePath = join(dir, 'overwrite.txt')
      writeFileSync(filePath, 'old content', 'utf-8')
      await handler.execute(
        {
          id: '1',
          name: 'write_file',
          arguments: { path: filePath, content: 'new content' },
        },
        ctx(dir),
      )
      const content = await import('node:fs').then((fs) =>
        fs.readFileSync(filePath, 'utf-8'),
      )
      expect(content).toBe('new content')
    })
  })

  describe('edit_file', () => {
    it('replaces old_string with new_string (literal mode)', async () => {
      const filePath = join(dir, 'edit.txt')
      writeFileSync(filePath, 'foo bar baz', 'utf-8')
      const result = await handler.execute(
        {
          id: '1',
          name: 'edit_file',
          arguments: { path: filePath, old_string: 'bar', new_string: 'qux' },
        },
        ctx(dir),
      )
      expect(result.isError).toBeFalsy()
      const content = await import('node:fs').then((fs) =>
        fs.readFileSync(filePath, 'utf-8'),
      )
      expect(content).toBe('foo qux baz')
    })

    it('returns isError when old_string not found (literal mode)', async () => {
      const filePath = join(dir, 'edit.txt')
      writeFileSync(filePath, 'foo bar baz', 'utf-8')
      const result = await handler.execute(
        {
          id: '1',
          name: 'edit_file',
          arguments: {
            path: filePath,
            old_string: 'notfound',
            new_string: 'qux',
          },
        },
        ctx(dir),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('not found')
    })

    it('works with regex pattern (regex=true)', async () => {
      const filePath = join(dir, 'regex-edit.txt')
      writeFileSync(filePath, 'foo123 bar456 baz', 'utf-8')
      const result = await handler.execute(
        {
          id: '1',
          name: 'edit_file',
          arguments: {
            path: filePath,
            old_string: '\\d+',
            new_string: 'NUM',
            regex: true,
          },
        },
        ctx(dir),
      )
      expect(result.isError).toBeFalsy()
      const content = await import('node:fs').then((fs) =>
        fs.readFileSync(filePath, 'utf-8'),
      )
      expect(content).toBe('fooNUM bar456 baz')
    })

    it('returns isError for invalid regex', async () => {
      const filePath = join(dir, 'bad-regex.txt')
      writeFileSync(filePath, 'test', 'utf-8')
      const result = await handler.execute(
        {
          id: '1',
          name: 'edit_file',
          arguments: {
            path: filePath,
            old_string: '[invalid',
            new_string: 'x',
            regex: true,
          },
        },
        ctx(dir),
      )
      expect(result.isError).toBe(true)
      expect(result.content).toContain('Invalid regex')
    })
  })
})
