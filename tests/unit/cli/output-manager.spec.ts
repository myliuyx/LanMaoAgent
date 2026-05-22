import { describe, it, expect, vi } from 'vitest'
import { OutputManager, centerLine } from '../../../apps/cli/src/ui/output-manager.js'

describe('centerLine', () => {
  it('pads short text equally on both sides', () => {
    const result = centerLine('hello', 20)
    // left=7 right=8 = 20 visible chars
    expect(result).toBe('       hello        ')
  })

  it('handles text longer than width (no negative padding)', () => {
    const result = centerLine('x'.repeat(100), 40)
    expect(result).toBe('x'.repeat(100))
  })

  it('strips ANSI for visible length calculation', () => {
    const green = '\x1B[32m'
    const reset = '\x1B[39m'
    const result = centerLine(`${green}ok${reset}`, 10)
    // visible='ok'=2, left=4 right=4 = 10 visible chars
    expect(result).toBe(`    ${green}ok${reset}    `)
  })

  it('handles empty string', () => {
    expect(centerLine('', 10)).toBe('          ')
  })
})

describe('OutputManager', () => {
  function mockStream(): NodeJS.WriteStream {
    return { write: vi.fn(), columns: 80 } as unknown as NodeJS.WriteStream
  }

  it('writeLine centers output', () => {
    const stdout = mockStream()
    const om = new OutputManager(stdout, {} as NodeJS.WriteStream)
    om.writeLine('hello')
    // width=80, visible=5, left=37 right=38
    const expected = ' '.repeat(37) + 'hello' + ' '.repeat(38) + '\n'
    expect(stdout.write).toHaveBeenCalledWith(expected)
  })

  it('updateToolLine uses \\r and no \\n', () => {
    const stdout = mockStream()
    const om = new OutputManager(stdout, {} as NodeJS.WriteStream)
    om.updateToolLine('running')
    // width=80, visible=7, left=36 right=37
    const expected = '\r' + ' '.repeat(36) + 'running' + ' '.repeat(37)
    expect(stdout.write).toHaveBeenCalledWith(expected)
  })

  it('clearToolLine writes spaces and \\r', () => {
    const stdout = mockStream()
    const om = new OutputManager(stdout, {} as NodeJS.WriteStream)
    om.updateToolLine('tool')
    vi.mocked(stdout.write).mockClear()
    om.clearToolLine()
    // After updateToolLine('tool'): prevToolLineWidth = 80
    expect(stdout.write).toHaveBeenCalledWith('\r' + ' '.repeat(80) + '\r')
  })

  it('clearToolLine is noop when nothing displayed', () => {
    const stdout = mockStream()
    const om = new OutputManager(stdout, {} as NodeJS.WriteStream)
    om.clearToolLine()
    expect(stdout.write).not.toHaveBeenCalled()
  })

  it('terminalWidth falls back to 80', () => {
    const stdout = { write: vi.fn() } as unknown as NodeJS.WriteStream
    const om = new OutputManager(stdout, {} as NodeJS.WriteStream)
    expect(om.terminalWidth).toBe(80)
  })
})
