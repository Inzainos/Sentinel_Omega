import js from '@eslint/js'
import typescriptEslint from 'typescript-eslint'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'

export default [
  { ignores: ['dist/', 'node_modules/', '.storybook/', 'eslint.config.js', 'storybook-static/', 'storybook-static/**', 'tailwind.config.js'] },
  ...typescriptEslint.config(
    js.configs.recommended,
    ...typescriptEslint.configs.recommended,
    {
      files: ['**/*.{ts,tsx}'],
      languageOptions: {
        parserOptions: {
          ecmaVersion: 'latest',
          sourceType: 'module',
        },
      },
      plugins: {
        react,
        'react-hooks': reactHooks,
      },
      rules: {
        ...react.configs.recommended.rules,
        ...reactHooks.configs.recommended.rules,
        'react/react-in-jsx-scope': 'off',
        '@typescript-eslint/no-explicit-any': 'warn',
        '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      },
    }
  ),
]