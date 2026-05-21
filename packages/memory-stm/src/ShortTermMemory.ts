import type { ChatMessage } from '@agent-platform/shared-types'

function extractToolSummary(content: string): string {
  const trimmed = content.substring(0, 500)
  try {
    const parsed = JSON.parse(trimmed)
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      const entries = Object.entries(parsed)
        .slice(0, 5)
        .map(([k, v]) => {
          const str = String(v)
          return `${k}: ${str.length > 50 ? str.substring(0, 50) + '...' : str}`
        })
      return entries.join(', ')
    }
    if (Array.isArray(parsed)) {
      return `[array length ${parsed.length}]`
    }
    return String(parsed).substring(0, 200)
  } catch {
    return content.substring(0, 200)
  }
}

export class ShortTermMemory {
  private messages: ChatMessage[] = []
  private maxCapacity: number
  private threshold: number
  private compactCount = 0
  private readonly MAX_COMPACT_COUNT = 5

  /** @param maxCapacity - Maximum message count. Use -1 for unlimited capacity. Defaults to 100. */
  constructor(maxCapacity = 100, threshold = 50) {
    this.maxCapacity = maxCapacity
    this.threshold = threshold
  }

  add(message: ChatMessage): void {
    const cloned = structuredClone(message)
    if (this.maxCapacity > 0 && this.messages.length >= this.maxCapacity) {
      this.messages.shift()
    }
    this.messages.push(cloned)
  }

  /** Reset compact count for a fresh session. */
  resetCompactCount(): void {
    this.compactCount = 0
  }

  getContext(): ChatMessage[] {
    return [...this.messages]
  }

  compact(): number {
    if (this.messages.length <= this.threshold) {
      return 0
    }

    // When MAX_COMPACT_COUNT is reached, switch to drop mode: remove oldest messages without inserting summary.
    // This prevents unbounded memory growth after repeated compactions.
    const n = Math.floor(this.threshold / 2)
    if (this.compactCount >= this.MAX_COMPACT_COUNT) {
      this.messages.splice(0, n)
      return n * 10 // Return a fixed estimate since we don't know exact token savings in drop mode
    }

    const oldMessages = this.messages.splice(0, n)

    const groups: Record<string, string[]> = { user: [], assistant: [], tool: [] }
    for (const msg of oldMessages) {
      const role = msg.role as string
      if (!groups[role]) continue
      const content = msg.content ?? ''
      groups[role].push(content.length > 200 ? content.substring(0, 200) : content)
    }

    const lines: string[] = []

    const formatTextGroup = (header: string, items: string[], prefix: string) => {
      if (items.length === 0) return
      lines.push(header)
      for (const item of items.slice(0, 10)) {
        lines.push(`${prefix} "${item}"`)
      }
    }

    const formatToolGroup = (header: string, items: string[]) => {
      if (items.length === 0) return
      lines.push(header)
      for (const item of items.slice(0, 10)) {
        const trimmed = extractToolSummary(item)
        lines.push(`- ${trimmed}`)
      }
    }

    formatTextGroup('[User Messages]', groups.user, '-')
    formatTextGroup('[Assistant Messages]', groups.assistant, '-')
    formatToolGroup('[Tool Results]', groups.tool)

    const firstUser = oldMessages.find((m) => m.role === 'user')
    const coreGoal = firstUser?.content
      ? firstUser.content.substring(0, 100)
      : ''

    lines.push(`[对话摘要：共 ${oldMessages.length} 轮对话，核心目标是${coreGoal}]`)

    const summary = lines.join('\n').trimEnd()
    this.messages.unshift({ role: 'system', content: summary })

    this.compactCount++

    const removedContent = oldMessages.map((m) => m.content ?? '').join('')
    const bytes = new TextEncoder().encode(removedContent).length
    return Math.floor(bytes / 3)
  }
}
