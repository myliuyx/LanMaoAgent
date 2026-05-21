import { describe, it, expect } from 'vitest'
import { render } from '../../../apps/cli/src/ui/renderer.js'

describe('renderer', () => {
  it('renders plain text unchanged', () => {
    expect(render('hello world')).toBe('hello world')
  })

  it('renders empty string as empty', () => {
    expect(render('')).toBe('')
  })

  it('renders **bold** text', () => {
    const result = render('hello **world**')
    expect(result).toContain('world')
    expect(result).not.toBe('hello **world**')
  })

  it('renders `inline code`', () => {
    const result = render('use `foo()`')
    expect(result).toContain('foo()')
    expect(result).not.toBe('use `foo()`')
  })

  it('renders # heading', () => {
    const result = render('# Title')
    expect(result).toContain('Title')
  })

  it('renders code block with syntax highlighting', () => {
    const result = render('```ts\nconst x = 1\n```')
    expect(result).toContain('const')
    expect(result).toContain('x')
  })

  it('renders code block without language', () => {
    const result = render('```\nplain text\n```')
    expect(result).toContain('plain text')
  })
})
