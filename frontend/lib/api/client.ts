import createClient from "openapi-fetch"

import type { paths } from "@/lib/api/types"

/**
 * Typed client for the backend API, for use from the browser.
 *
 * It points at `/api/proxy`, not at the backend directly: the access token
 * lives in an httpOnly cookie that JavaScript cannot read, and the proxy route
 * handler is what turns it into an `Authorization` header. Calling the backend
 * straight from the browser would send no credentials at all.
 *
 * The `paths` type is generated from the backend's OpenAPI schema — run
 * `npm run generate-api-types` after changing a route or a schema, so a broken
 * contract shows up as a type error instead of a runtime surprise.
 */
export const apiClient = createClient<paths>({ baseUrl: "/api/proxy" })

/** Server-side client, for Server Components and Server Actions. */
export function createServerClient(token: string) {
  return createClient<paths>({
    baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    headers: { Authorization: `Bearer ${token}` },
  })
}
