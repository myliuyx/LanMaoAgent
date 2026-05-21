import pc from 'picocolors'
import os from 'node:os'
import path, { dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import fs from 'node:fs'

const __dirname = dirname(fileURLToPath(import.meta.url))

// ─────────────────────────────────────────────
// Unicode block characters for pixel-art logos.
// These tile vertically to form solid squares:
//   Upper half + Lower half = full block
//   Left  half + Right half = full block (horizontally)
// ─────────────────────────────────────────────

// Full blocks — dark → light shade
const FULL    = '█'   // solid black
const SHADE3  = '▓'   // dark shade
const SHADE2  = '▒'   // medium shade
const SHADE1  = '░'   // light shade

// Half blocks (upper/lower) — combine vertically to form full blocks
const UPPER   = '▀'   // upper half
const LOWER   = '▄'   // lower half

// Side halves — combine horizontally
const HALF_L  = '▌'   // left half
const HALF_R  = '▐'   // right half

// "White" quarter blocks for empty/background areas
const WBR     = '▘'   // bottom-right (white)
const WBL     = '▝'   // bottom-left (white)
const WTR     = '▖'   // top-right (white)
const WTL     = '▗'   // top-left (white)

// Mixed quarter blocks for diagonal transitions
const WBRD  = '▙'   // bottom half white
const WTLD  = '▚'   // top-left white, rest dark
const WBRT  = '▛'   // right half white
const WBLC  = '▜'   // left half filled

function getVersion(): string {
  // Try package.json from the cli dist dir (runs as ESM)
  const candidates = [
    path.join(__dirname, '../../../package.json'),
    path.join(__dirname, '../../package.json'),
    path.join(process.cwd(), 'package.json'),
  ]
  for (const p of candidates) {
    try {
      const raw = JSON.parse(fs.readFileSync(p, 'utf-8')) as { version?: string }
      if (raw.version) return raw.version
    } catch { /* next */ }
  }

  // Fallback: git describe
  try {
    const cp = require('child_process')
    const tag = cp.execSync("git describe --tags --always 2>/dev/null", {
      cwd: path.join(__dirname, '../../..'),
      encoding: 'utf-8',
    }).trim()
    return tag.replace(/^v/, '')
  } catch {
    return '?'
  }
}

export function renderBanner(): string {
  const version = getVersion()
  const cwd = path.basename(process.cwd())
  const homedir = path.basename(os.homedir())

  // ── Logo: pixelated "A" (8 cells × 2 rows) ──
  //   ▐▛███▜▌    row A — right half + dark quarter + full×3 + dark quarter + left half
  //   ▝▜█████▛▘  row B — white corner + dark quarter + full×5 + white quarter

  const logoTop    = `${HALF_R}${WBRT}${FULL}${FULL}${FULL}${WBLC}${HALF_L}`
  const logoBottom = `${WBL}${WBLC}${FULL}${FULL}${FULL}${FULL}${FULL}${WBRT}${WBR}`

  // Leading space on row A, trailing spaces to align text at col 11
  const line1 = ` ${logoTop}   agent platform v${version}`
  const line2 = `${logoBottom}  ${os.type().replace('Darwin', 'macOS')} · ~${homedir} · ${cwd}`

  return `${line1}\n${line2}`
}

export const theme = {
  prompt:     pc.magenta,
  heading1:   (s: string) => pc.bold(pc.yellow(s)),
  heading2:   (s: string) => pc.bold(pc.cyan(s)),
  bold:       pc.bold,
  inlineCode: (s: string) => pc.bgCyan(pc.white(s)),
  codeFence:  pc.dim,
  blockquote: (s: string) => pc.dim(pc.italic(s)),
  link:       (s: string) => pc.blue(pc.underline(s)),
  filePath:   (s: string) => pc.cyan(pc.underline(s)),
  toolRunning: pc.dim,
  toolDone:   pc.green,
  toolError:  pc.red,
  error:      (s: string) => pc.bold(pc.red(s)),
  queue:      (s: string) => pc.dim(pc.yellow(s)),
  cancel:     pc.dim,
  separator:  pc.dim,
}
