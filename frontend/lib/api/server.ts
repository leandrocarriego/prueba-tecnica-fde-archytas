import { cookies } from 'next/headers'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_PREFIX = '/api/v1'

/** A request that hangs is a request that failed. */
const TIMEOUT_MS = 10_000

/**
 * Reading the API from a Server Component.
 *
 * The browser never talks to the backend directly — that is what
 * `app/api/proxy` is for — but a Server Component is already on the server and
 * holds the session cookie, so it calls the API itself and ships rendered HTML.
 * One fewer round trip, and the token never leaves the server.
 */
export async function fetchFromApi<T>(path: string): Promise<T | null> {
  const token = (await cookies()).get('access_token')?.value
  if (!token) return null

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS)
  try {
    const response = await fetch(`${API_URL}${API_PREFIX}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
      signal: controller.signal,
    })
    if (!response.ok) return null
    return (await response.json()) as T
  } catch {
    // The backend is unreachable. The page renders its empty state rather than
    // a stack trace: what it shows is prices, and "no pudimos traerlos" is an
    // answer a person can act on.
    return null
  } finally {
    clearTimeout(timeout)
  }
}
