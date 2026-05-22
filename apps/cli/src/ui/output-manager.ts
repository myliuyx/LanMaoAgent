function stripAnsi(text: string): string {
  // eslint-disable-next-line no-control-regex
  return text.replace(/\u001b\[[0-9;]*m/g, '')
}

export function centerLine(line: string, width: number): string {
  const visible = stripAnsi(line)
  const leftPad = Math.max(0, Math.floor((width - visible.length) / 2))
  const rightPad = Math.max(0, width - visible.length - leftPad)
  return ' '.repeat(leftPad) + line + ' '.repeat(rightPad)
}

export class OutputManager {
  private prevToolLineWidth = 0

  constructor(
    private stdout: NodeJS.WriteStream,
    private stderr: NodeJS.WriteStream,
  ) {}

  get terminalWidth(): number {
    return this.stdout.columns ?? 80
  }

  writeLine(text: string): void {
    const width = this.terminalWidth
    const centered = text
      .split('\n')
      .map((line) => (line.trim() ? centerLine(line, width) : line))
      .join('\n')
    this.stdout.write(centered + '\n')
  }

  writeContent(text: string): void {
    const width = this.terminalWidth
    const centered = text
      .split('\n')
      .map((line) => (line.trim() ? centerLine(line, width) : line))
      .join('\n')
    this.stdout.write(centered + '\n')
  }

  updateToolLine(text: string): void {
    const width = this.terminalWidth
    const padded = centerLine(text, width)
    const lineLen = stripAnsi(padded).length
    const clear = lineLen < this.prevToolLineWidth
      ? ' '.repeat(this.prevToolLineWidth - lineLen)
      : ''
    this.stdout.write('\r' + padded + clear)
    this.prevToolLineWidth = Math.max(lineLen, this.prevToolLineWidth)
  }

  clearToolLine(): void {
    if (this.prevToolLineWidth > 0) {
      this.stdout.write('\r' + ' '.repeat(this.prevToolLineWidth) + '\r')
      this.prevToolLineWidth = 0
    }
  }
}
