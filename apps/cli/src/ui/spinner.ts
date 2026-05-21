import ora, { type Ora } from 'ora'

export class Spinner {
  private instance?: Ora

  start(text: string): void {
    this.stop()
    this.instance = ora({ text, discardStdin: false }).start()
  }

  setText(text: string): void {
    if (this.instance) {
      this.instance.text = text
    }
  }

  stop(): void {
    if (this.instance) {
      this.instance.stop()
      this.instance = undefined
    }
  }
}
