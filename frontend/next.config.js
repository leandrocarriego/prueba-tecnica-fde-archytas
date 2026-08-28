/** @type {import('next').NextConfig} */

// Backend base URL. Everything that talks to FastAPI goes through the server side:
// - Server Actions and route handlers under `app/api/auth/*` call `${NEXT_PUBLIC_API_URL}/api/v1/...`
// - client-side calls go to `/api/proxy/<path>`, handled by `app/api/proxy/[...path]/route.ts`,
//   which injects `Authorization: Bearer <token>` from the httpOnly session cookie.
// That proxy is a route handler on purpose: a `rewrites()` entry cannot read the httpOnly
// cookie nor add the auth header, so it would expose the API unauthenticated.
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const nextConfig = {
  reactStrictMode: true,
  output: process.env.NODE_ENV === 'production' ? 'standalone' : undefined,
  env: {
    NEXT_PUBLIC_API_URL: API_URL,
  },
  // Permitir Server Actions cuando se usa un túnel de desarrollo
  experimental: {
    serverActions: {
      allowedOrigins: ['localhost:3000', '*.devtunnels.ms', '*.brs.devtunnels.ms'],
    },
  },
}

module.exports = nextConfig
