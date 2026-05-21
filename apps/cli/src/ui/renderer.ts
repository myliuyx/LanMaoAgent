import { marked, Token, Tokens } from 'marked'
import pc from 'picocolors'

const KEYWORDS =
  /\b(async|await|break|case|catch|class|const|continue|debugger|default|delete|do|else|export|extends|false|finally|for|function|if|import|in|instanceof|let|new|null|of|return|static|super|switch|this|throw|true|try|typeof|var|void|while|with|yield|interface|type|enum|implements|private|protected|public|abstract|readonly|declare|namespace|module|from|as|def|end|puts|print|require|include|defmodule|defstruct|defn|fn|do|end|nil|true|false|and|or|not|if|unless|else|elsif|case|when|then|raise|rescue|catch|throw|import|package|object|trait|val|var|def|class|object|trait|extends|with|sealed|abstract|lazy|implicit|match|case)\b/

function highlight(text: string): string {
  const lines = text.split('\n')
  return lines.map((line) => {
    let highlighted = line
    // Strings (double, single, template literals)
    highlighted = highlighted.replace(
      /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)/g,
      (match) => pc.green(match),
    )
    // Single-line comments
    highlighted = highlighted.replace(/(\/\/.*$|#.*$)/gm, (match) => pc.dim(match))
    // Multi-line comments (simple single-line match for /* ... */ on one line)
    highlighted = highlighted.replace(
      /\/\*[\s\S]*?\*\//g,
      (match) => pc.dim(match),
    )
    // Numbers
    highlighted = highlighted.replace(
      /\b(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|0[xX][0-9a-fA-F]+|0[bB][01]+)\b/g,
      (match) => pc.yellow(match),
    )
    // Keywords
    highlighted = highlighted.replace(KEYWORDS, (match) => pc.cyan(match))
    return highlighted
  }).join('\n')
}

type InlineToken = Token & { tokens?: InlineToken[] }

function renderInline(tokens: InlineToken[]): string {
  return tokens
    .map((t) => {
      switch (t.type) {
        case 'strong':
          return pc.bold(renderInline(t.tokens ?? []))
        case 'em':
          return pc.italic(renderInline(t.tokens ?? []))
        case 'codespan':
          return pc.bgCyan(pc.white(t.text))
        case 'link':
          return `${pc.blue(pc.underline(t.text))}`
        case 'text':
          return t.text
        default:
          return 'raw' in t ? (t as { raw: string }).raw : ''
      }
    })
    .join('')
}

function renderBlock(tokens: Token[]): string {
  return tokens
    .map((t) => {
      switch (t.type) {
        case 'heading': {
          const ht = t as Tokens.Heading
          const inner = renderInline(ht.tokens as InlineToken[])
          return (ht.depth === 1 ? pc.bold(pc.yellow(inner)) : pc.bold(pc.cyan(inner))) + '\n'
        }

        case 'paragraph': {
          const pt = t as Tokens.Paragraph
          return renderInline(pt.tokens as InlineToken[]) + '\n\n'
        }

        case 'code': {
          const ct = t as Tokens.Code
          const lang = ct.lang ?? ''
          const header = lang ? pc.dim('```' + lang) : pc.dim('```')
          const body = highlight(ct.text)
          return header + '\n' + body + '\n' + pc.dim('```') + '\n\n'
        }

        case 'blockquote':
          return pc.dim(pc.italic((t as Tokens.Blockquote).text)) + '\n\n'

        case 'list': {
          const lt = t as Tokens.List
          return (
            lt.items
              .map((item: Tokens.ListItem) => {
                const prefix = lt.ordered ? ' 1. ' : ' • '
                return prefix + item.text
              })
              .join('\n') + '\n\n'
          )
        }

        case 'hr':
          return pc.dim('---') + '\n\n'

        case 'space':
          return '\n'

        default:
          return 'raw' in t ? (t as { raw: string }).raw + '\n' : ''
      }
    })
    .join('')
}

export function render(text: string): string {
  if (!text) return ''
  const tokens = marked.lexer(text)
  const result = renderBlock(tokens).trimEnd()
  return result || text
}
