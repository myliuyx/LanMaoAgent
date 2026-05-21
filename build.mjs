import { build } from 'esbuild'

await build({
  entryPoints: ['apps/cli/src/index.ts'],
  bundle: true,
  format: 'esm',
  platform: 'node',
  target: 'node20.0.0',
  outfile: 'apps/cli/dist/cli.js',
  external: [
    'node:crypto',
    'node:fs',
    'node:path',
    'node:child_process',
    'node:os',
    'node:events',
  ],
})
