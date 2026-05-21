import { defineConfig } from 'vitest/config'
import path from 'node:path'

export default defineConfig({
  resolve: {
    alias: {
      '@agent-platform/shared-types': path.resolve(__dirname, 'packages/shared-types/src/index.ts'),
      '@agent-platform/memory-stm': path.resolve(__dirname, 'packages/memory-stm/src/index.ts'),
      '@agent-platform/llm-adapter': path.resolve(__dirname, 'packages/llm-adapter/src/index.ts'),
      '@agent-platform/tool-core': path.resolve(__dirname, 'packages/tool-core/src/index.ts'),
      '@agent-platform/tools-filesystem': path.resolve(__dirname, 'packages/tools/filesystem/src/index.ts'),
      '@agent-platform/tools-git': path.resolve(__dirname, 'packages/tools/git/src/index.ts'),
      '@agent-platform/tools-terminal': path.resolve(__dirname, 'packages/tools/terminal/src/index.ts'),
      '@agent-platform/platform': path.resolve(__dirname, 'packages/platform/src/index.ts'),
    },
  },
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      statements: 80,
      branches: 80,
      functions: 80,
      lines: 80,
    },
  },
})
