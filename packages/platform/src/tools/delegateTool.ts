import { randomUUID } from 'node:crypto'
import type {
  Agent,
  ToolHandler,
  ToolCall,
  ToolResult,
  ToolExecutionContext,
  ToolDefinition,
  AgentConfig,
} from '@agent-platform/shared-types'
import type { LLMAdapter } from '@agent-platform/llm-adapter'
import type { ToolRegistry } from '@agent-platform/tool-core'
import { runAgentLoop } from '@agent-platform/tool-core'
import { ShortTermMemory } from '@agent-platform/memory-stm'

export interface AgentResolver {
  get(id: string): Agent | undefined
}

export class DelegateToAgentHandler implements ToolHandler {
  readonly id = 'delegate_to_agent'

  constructor(
    private resolver: AgentResolver,
    private llm: LLMAdapter,
    private registry: ToolRegistry,
    private compressionRatio: number = 0.8,
    private maxToolRetries: number = 2,
    private agents: AgentConfig[] = [],
  ) {}

  getTools(): ToolDefinition[] {
    const agentLines = this.agents
      .filter((a) => a.id !== 'orchestrator')
      .map(
        (a) =>
          `- ${a.id}: ${a.description || a.name}`,
      )
      .join('\n')

    return [
      {
        name: 'delegate_to_agent',
        description: `Delegate a task to a specialized sub-agent.\n\nAvailable agents:\n${agentLines || '(none)'}`,
        parameters: {
          type: 'object',
          properties: {
            agentId: {
              type: 'string',
              description: 'The agent to delegate to',
            },
            task: {
              type: 'string',
              description: 'The task description to delegate',
            },
            context: {
              type: 'string',
              description: 'Optional conversation context from parent (e.g., prior tool results)',
            },
          },
          required: ['agentId', 'task'],
        },
      },
    ]
  }

  async execute(
    call: ToolCall,
    ctx: ToolExecutionContext,
  ): Promise<ToolResult> {
    const args = call.arguments as { agentId: string; task: string }
    const targetAgent = this.resolver.get(args.agentId)

    if (!targetAgent) {
      return { content: 'Unknown agent', isError: true }
    }

    const subSessionId = `sub-${randomUUID()}`
    const stm = new ShortTermMemory()
    const delegateCtx: ToolExecutionContext = {
      ...ctx,
      sessionId: subSessionId,
      depth: (ctx.depth ?? 0) + 1,
    }

    // Attach optional conversation context passed by the orchestrator.
    const parentContext = (call.arguments as Record<string, unknown>)['context']
    const taskWithHistory = parentContext
      ? `${args.task}\n\n## Previous Conversation Context\n${String(parentContext).substring(0, 2000)}\n\nPlease handle this task and provide your final result.`
      : args.task

    const fullMessagesInner = [
      { role: 'system' as const, content: targetAgent.systemPrompt },
      { role: 'user' as const, content: taskWithHistory },
    ]

    const result = await runAgentLoop({
      agent: targetAgent,
      messages: fullMessagesInner,
      registry: this.registry,
      ctx: delegateCtx,
      llm: this.llm,
      memory: stm,
      compressionRatio: this.compressionRatio,
      maxToolRetries: this.maxToolRetries,
      depth: delegateCtx.depth,
      onToolStart: ctx.onToolStart,
      onToolFinish: ctx.onToolFinish,
      onToolRetry: ctx.onToolRetry,
    })

    if (result.status === 'aborted') {
      return { content: 'Sub-agent aborted', isError: true }
    }

    if (result.status !== 'completed') {
      const reason = result.error || `agent ended with status '${result.status}'`
      return { content: JSON.stringify({ agentId: args.agentId, error: reason }), isError: true }
    }

    if (!result.output) {
      return { content: JSON.stringify({ agentId: args.agentId, error: 'no output from sub-agent' }), isError: true }
    }

    return {
      content: JSON.stringify({ agentId: args.agentId, output: result.output }),
      isError: false,
    }
  }
}
