import { describe, it, expect } from 'vitest'

describe('Spinner', () => {
  it('start/stop does not throw', async () => {
    const { Spinner } = await import('../../../apps/cli/src/ui/spinner.js')
    const s = new Spinner()
    expect(() => {
      s.start('working...')
      s.stop()
    }).not.toThrow()
  })

  it('setText after start does not throw', async () => {
    const { Spinner } = await import('../../../apps/cli/src/ui/spinner.js')
    const s = new Spinner()
    s.start('working...')
    expect(() => s.setText('still working...')).not.toThrow()
    s.stop()
  })

  it('double start does not throw', async () => {
    const { Spinner } = await import('../../../apps/cli/src/ui/spinner.js')
    const s = new Spinner()
    s.start('first')
    expect(() => s.start('second')).not.toThrow()
    s.stop()
  })

  it('stop without start does not throw', async () => {
    const { Spinner } = await import('../../../apps/cli/src/ui/spinner.js')
    const s = new Spinner()
    expect(() => s.stop()).not.toThrow()
  })
})
