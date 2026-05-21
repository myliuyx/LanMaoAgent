import { describe, it, expect } from 'vitest'
import { ShortTermMemory } from '@agent-platform/memory-stm'
import type { ChatMessage } from '@agent-platform/shared-types'

function addMessages(stm: ShortTermMemory, role: ChatMessage['role'], count: number, prefix = 'msg') {
  for (let i = 0; i < count; i++) {
    stm.add({ role, content: `${prefix}-${i}` })
  }
}

describe('ShortTermMemory', () => {
  describe('add / getContext', () => {
    it('add appends message to internal storage', () => {
      const stm = new ShortTermMemory()
      stm.add({ role: 'user', content: 'hello' })
      expect(stm.getContext()).toHaveLength(1)
    })

    it('getContext returns a snapshot, not internal reference', () => {
      const stm = new ShortTermMemory()
      stm.add({ role: 'user', content: 'test' })
      const ctx = stm.getContext()
      ctx.push({ role: 'user', content: 'injected' })
      expect(stm.getContext()).toHaveLength(1)
    })

    it('empty STM getContext returns []', () => {
      const stm = new ShortTermMemory()
      expect(stm.getContext()).toEqual([])
    })

    it('add does not mutate the original message (structuredClone)', () => {
      const stm = new ShortTermMemory()
      const original: ChatMessage = { role: 'user', content: 'original' }
      stm.add(original)
      original.content = 'mutated'
      const [stored] = stm.getContext()
      expect(stored.content).toBe('original')
    })

    it('accepts 100 consecutive messages without issue', () => {
      const stm = new ShortTermMemory()
      for (let i = 0; i < 100; i++) {
        stm.add({ role: 'user', content: `msg-${i}` })
      }
      expect(stm.getContext()).toHaveLength(100)
    })
  })

  describe('maxCapacity (ring buffer)', () => {
    it('wraps oldest messages when exceeding maxCapacity', () => {
      const stm = new ShortTermMemory(5)
      for (let i = 0; i < 7; i++) {
        stm.add({ role: 'user', content: `msg-${i}` })
      }
      const ctx = stm.getContext()
      expect(ctx).toHaveLength(5)
      expect(ctx[0].content).toBe('msg-2')
      expect(ctx[4].content).toBe('msg-6')
    })

    it('maxCapacity 0 means unbounded', () => {
      const stm = new ShortTermMemory(0)
      for (let i = 0; i < 10; i++) {
        stm.add({ role: 'user', content: `msg-${i}` })
      }
      expect(stm.getContext()).toHaveLength(10)
    })
  })

  describe('compact', () => {
    const compactWithMessages = (
      messages: { role: ChatMessage['role']; content: string }[],
    ) => {
      const stm = new ShortTermMemory()
      for (const m of messages) {
        stm.add(m)
      }
      // Pad to exceed threshold (need > 50 total)
      for (let i = 0; i < 55; i++) {
        stm.add({ role: 'user', content: 'padding' })
      }
      stm.compact()
      return stm.getContext()[0].content as string
    }

    it('extracts JSON object keys from tool messages', () => {
      const summary = compactWithMessages([
        { role: 'tool', content: JSON.stringify({ file: 'test.ts', result: 'ok' }) },
      ])
      expect(summary).toContain('file: test.ts')
      expect(summary).toContain('result: ok')
    })

    it('handles JSON array tool messages', () => {
      const summary = compactWithMessages([
        { role: 'tool', content: JSON.stringify([1, 2, 3]) },
      ])
      expect(summary).toContain('array length 3')
    })

    it('truncates long values in JSON tool messages', () => {
      const longVal = 'a'.repeat(100)
      const summary = compactWithMessages([
        { role: 'tool', content: JSON.stringify({ data: longVal }) },
      ])
      expect(summary).toContain('data: ')
      expect(summary).toContain('...')
    })

    it('handles JSON primitive (string) tool messages', () => {
      const summary = compactWithMessages([
        { role: 'tool', content: '"just-a-string"' },
      ])
      expect(summary).toContain('just-a-string')
    })

    it('truncates tool content longer than 200 chars', () => {
      const longContent = 'x'.repeat(300)
      const summary = compactWithMessages([
        { role: 'tool', content: longContent },
      ])
      expect(summary).toContain('x'.repeat(200))
      expect(summary).not.toContain('x'.repeat(201))
    })
    it('returns 0 when below threshold', () => {
      const stm = new ShortTermMemory()
      addMessages(stm, 'user', 30)
      const released = stm.compact()
      expect(released).toBe(0)
      expect(stm.getContext()).toHaveLength(30)
    })

    it('compresses oldest messages into a role-grouped summary', () => {
      const stm = new ShortTermMemory()
      addMessages(stm, 'user', 8)
      addMessages(stm, 'assistant', 8)
      addMessages(stm, 'tool', 9)
      addMessages(stm, 'user', 35)
      const before = stm.getContext().length
      stm.compact()
      const after = stm.getContext().length
      expect(after).toBeLessThan(before)
      const summary = stm.getContext()[0]
      expect(summary.role).toBe('system')
      expect(summary.content).toContain('[User Messages]')
      expect(summary.content).toContain('[Assistant Messages]')
      expect(summary.content).toContain('[Tool Results]')
    })

    it('preserves user/assistant/tool distinction in summary', () => {
      const stm = new ShortTermMemory()
      addMessages(stm, 'user', 5, 'user-msg')
      addMessages(stm, 'assistant', 5, 'asst-msg')
      addMessages(stm, 'tool', 15, 'tool-msg')
      addMessages(stm, 'user', 40, 'keep-me')
      stm.compact()
      const summary = stm.getContext()[0].content as string
      expect(summary).toContain('[User Messages]')
      expect(summary).toContain('[Assistant Messages]')
      expect(summary).toContain('[Tool Results]')
      const userSection = summary.split('[Assistant Messages]')[0]
      expect(userSection).toContain('user-msg')
      expect(userSection).not.toContain('asst-msg')
    })

    it('returns token count estimate (UTF-8 bytes / 3)', () => {
      const stm = new ShortTermMemory()
      addMessages(stm, 'user', 60, 'hello')
      const released = stm.compact()
      expect(released).toBeGreaterThan(0)
      expect(Number.isInteger(released)).toBe(true)
    })

    it('consecutive compact calls return 0 after first compression', () => {
      const stm = new ShortTermMemory()
      addMessages(stm, 'user', 60)
      stm.compact()
      expect(stm.compact()).toBe(0)
    })
  })
})
