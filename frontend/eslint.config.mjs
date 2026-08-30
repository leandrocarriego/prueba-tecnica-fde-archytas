// ESLint 9 flat config. Next 16 removed `next lint`, so ESLint is invoked
// directly (`npm run lint`) and eslint-config-next is consumed as a flat config
// export rather than through the legacy `.eslintrc.json`.
import nextCoreWebVitals from 'eslint-config-next/core-web-vitals'
import nextTypescript from 'eslint-config-next/typescript'

const config = [
  {
    ignores: [
      '.next/**',
      'node_modules/**',
      'next-env.d.ts',
      // Generated from the backend's OpenAPI schema; not ours to lint.
      'lib/api/types.ts',
    ],
  },
  ...nextCoreWebVitals,
  ...nextTypescript,
]

export default config
