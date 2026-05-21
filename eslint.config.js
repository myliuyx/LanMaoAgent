import eslint from '@eslint/js'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['**/dist/', '**/node_modules/'] },
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  {
    rules: {
      'no-console': 'error',
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
  {
    files: ['packages/shared-types/src/logger.ts', 'tests/**/*.spec.ts'],
    rules: { 'no-console': 'off' },
  },
)
