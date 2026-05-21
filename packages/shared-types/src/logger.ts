export interface Logger {
  info(msg: string, meta?: Record<string, unknown>): void
  warn(msg: string, meta?: Record<string, unknown>): void
  error(msg: string, meta?: Record<string, unknown>): void
  debug(msg: string, meta?: Record<string, unknown>): void
}

export const consoleLogger: Logger = {
  info: (msg, meta) => console.log(`[INFO] ${msg}${meta ? ' ' + JSON.stringify(meta) : ''}`),
  warn: (msg, meta) => console.warn(`[WARN] ${msg}${meta ? ' ' + JSON.stringify(meta) : ''}`),
  error: (msg, meta) => console.error(`[ERROR] ${msg}${meta ? ' ' + JSON.stringify(meta) : ''}`),
  debug: (msg, meta) => {
    if (process.env.DEBUG === '1') {
      console.debug(`[DEBUG] ${msg}${meta ? ' ' + JSON.stringify(meta) : ''}`)
    }
  },
}
