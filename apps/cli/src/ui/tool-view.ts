import pc from 'picocolors'
import type { ToolCall } from '@agent-platform/platform'

const AGENT_LABELS: Record<string, string> = {
  orchestrator: '编排',
  'coding-agent': '编码',
  planner: '规划',
  reviewer: '审查',
  tester: '测试',
}

function agentTag(agentId: string): string {
  const label = AGENT_LABELS[agentId] ?? agentId
  return pc.dim(`[${label}]`)
}

export class ToolView {
  constructor(private write: (line: string) => void = (s) => process.stdout.write(s + '\n')) {}

  onStart(call: ToolCall, agentId: string): void {
    const args = JSON.stringify(call.arguments)
    this.write(`${agentTag(agentId)} ⎿  ${pc.dim(call.name + '(' + args + ')')}`)
  }

  onFinish(
    call: ToolCall,
    result: { content: string; isError: boolean },
    agentId: string,
  ): void {
    if (result.isError) {
      this.write(`${agentTag(agentId)} ⎿  ${pc.red(call.name + ' error: ' + result.content)}`)
    } else {
      const summary = result.content.length + ' chars'
      this.write(`${agentTag(agentId)} ⎿  ${pc.green('✓ ' + call.name)} ${pc.dim('(' + summary + ')')}`)
    }
  }

  onRetry(call: ToolCall, attempt: number, maxAttempts: number, agentId: string): void {
    this.write(`${agentTag(agentId)} ⎿  ${pc.yellow('↻ ' + call.name + ` (retry ${attempt}/${maxAttempts})`)}`)
  }
}
