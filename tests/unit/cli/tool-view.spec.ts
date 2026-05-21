import { describe, it, expect, vi } from 'vitest'
import { ToolView } from '../../../apps/cli/src/ui/tool-view.js'

describe('ToolView', () => {
  it('onStart outputs formatted tool call line', () => {
    const write = vi.fn()
    const tv = new ToolView(write)
    tv.onStart({ id: 'tc1', name: 'read_file', arguments: { path: '/f' } })
    expect(write).toHaveBeenCalledTimes(1)
    expect(write.mock.calls[0][0]).toContain('read_file')
  })

  it('onFinish outputs result line', () => {
    const write = vi.fn()
    const tv = new ToolView(write)
    tv.onStart({ id: 'tc1', name: 'read_file', arguments: { path: '/f' } })
    write.mockClear()
    tv.onFinish(
      { id: 'tc1', name: 'read_file', arguments: { path: '/f' } },
      { content: 'file data', isError: false },
    )
    expect(write).toHaveBeenCalledTimes(1)
    expect(write.mock.calls[0][0]).toContain('read_file')
  })

  it('onError outputs error line', () => {
    const write = vi.fn()
    const tv = new ToolView(write)
    tv.onStart({ id: 'tc1', name: 'read_file', arguments: { path: '/f' } })
    write.mockClear()
    tv.onFinish(
      { id: 'tc1', name: 'read_file', arguments: { path: '/f' } },
      { content: 'error msg', isError: true },
    )
    expect(write.mock.calls[0][0]).toContain('error')
  })
})
