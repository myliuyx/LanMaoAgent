import { describe, it, expect, vi } from 'vitest'
import { ToolView } from '../../../apps/cli/src/ui/tool-view.js'
import { OutputManager } from '../../../apps/cli/src/ui/output-manager.js'

describe('ToolView', () => {
  function mockToolView(): { om: OutputManager; tv: ToolView } {
    const stdout = { write: vi.fn(), columns: 80 } as unknown as NodeJS.WriteStream
    const om = new OutputManager(stdout, {} as NodeJS.WriteStream)
    const tv = new ToolView(om)
    return { om, tv }
  }

  it('onStart calls updateToolLine with tool call info', () => {
    const { om, tv } = mockToolView()
    const write = vi.spyOn(om, 'updateToolLine')
    tv.onStart({ id: 'tc1', name: 'read_file', arguments: { path: '/f' } }, 'coding-agent')
    expect(write).toHaveBeenCalledTimes(1)
    expect(write.mock.calls[0][0]).toContain('read_file')
  })

  it('onFinish calls updateToolLine with result summary', () => {
    const { om, tv } = mockToolView()
    const write = vi.spyOn(om, 'updateToolLine')
    tv.onFinish(
      { id: 'tc1', name: 'read_file', arguments: { path: '/f' } },
      { content: 'file data', isError: false },
      'coding-agent',
    )
    expect(write).toHaveBeenCalledTimes(1)
    expect(write.mock.calls[0][0]).toContain('read_file')
  })

  it('onFinish with error calls updateToolLine with error', () => {
    const { om, tv } = mockToolView()
    const write = vi.spyOn(om, 'updateToolLine')
    tv.onFinish(
      { id: 'tc1', name: 'read_file', arguments: { path: '/f' } },
      { content: 'error msg', isError: true },
      'coding-agent',
    )
    expect(write.mock.calls[0][0]).toContain('error')
  })

  it('onRetry calls updateToolLine with retry info', () => {
    const { om, tv } = mockToolView()
    const write = vi.spyOn(om, 'updateToolLine')
    tv.onRetry(
      { id: 'tc1', name: 'read_file', arguments: { path: '/f' } },
      1, 3, 'coding-agent',
    )
    expect(write).toHaveBeenCalledTimes(1)
    expect(write.mock.calls[0][0]).toContain('↻')
  })
})
