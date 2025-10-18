module.exports = {
  root: true,
  env: {
    es2021: true,
    node: true,
  },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    project: ['./tsconfig.json'],
    tsconfigRootDir: __dirname,
    sourceType: 'module',
    ecmaVersion: 2022,
  },
  plugins: ['@typescript-eslint', 'import'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:import/recommended',
    'plugin:import/typescript',
    'next/core-web-vitals',
    'prettier',
  ],
  settings: {
    'import/resolver': {
      typescript: {
        project: [
          './packages/shared/tsconfig.json',
          './packages/api/tsconfig.json',
          './apps/web/tsconfig.json',
        ],
        alwaysTryTypes: true,
      },
      node: {
        extensions: ['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'],
      },
    },
  },
  ignorePatterns: ['dist', 'node_modules', 'apps/web/.next'],
  overrides: [
    {
      files: ['apps/web/**/*.{ts,tsx}'],
      env: { browser: true },
      parserOptions: {
        project: ['./apps/web/tsconfig.json'],
        tsconfigRootDir: __dirname,
      },
    },
    {
      files: ['packages/api/**/*.{ts,tsx}'],
      parserOptions: {
        project: ['./packages/api/tsconfig.json'],
        tsconfigRootDir: __dirname,
      },
    },
    {
      files: ['packages/shared/**/*.{ts,tsx}'],
      parserOptions: {
        project: ['./packages/shared/tsconfig.json'],
        tsconfigRootDir: __dirname,
      },
    },
    {
      files: ['**/*.test.ts'],
      rules: {
        '@typescript-eslint/no-unsafe-assignment': 'off',
        '@typescript-eslint/no-unsafe-call': 'off',
        '@typescript-eslint/no-unsafe-member-access': 'off',
        '@typescript-eslint/no-unsafe-return': 'off',
      },
    },
  ],
  rules: {
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    '@typescript-eslint/no-floating-promises': 'error',
    '@typescript-eslint/no-misused-promises': [
      'error',
      {
        checksVoidReturn: {
          attributes: false,
        },
      },
    ],
    'import/order': [
      'error',
      {
        'newlines-between': 'always',
        alphabetize: { order: 'asc', caseInsensitive: true },
      },
    ],
    'import/no-named-as-default': 'off',
    'import/no-named-as-default-member': 'off',
  },
};
