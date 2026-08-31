import { cookies } from 'next/headers'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_PREFIX = '/api/v1'

/** A request that hangs is a request that failed. */
const TIMEOUT_MS = 10_000

/**
 * Why a read came back without data.
 *
 * `unauthorized` is the API answering "not for you"; `unavailable` is the API
 * not answering at all; `missing` is it answering that there is nothing there.
 * They are three different sentences on screen, and a screen that cannot tell
 * them apart ends up blaming a person for an outage: it sends them to ask the
 * owner for a permission they already have, over a backend the owner cannot
 * fix from the permissions screen.
 */
export type ReadFailure = 'unauthorized' | 'missing' | 'unavailable'

/** The answer to a read: the data, or why there is none. */
export type ApiRead<T> =
  | { ok: true; data: T }
  | { ok: false; failure: ReadFailure; status: number | null }

/**
 * The status, read as one of the three answers a screen can write down.
 *
 * A 401 and a 403 are the same sentence to whoever is reading — the difference
 * between an expired session and a section that is not theirs is settled by
 * the route guard, not by a page. Everything else, a 500 and a 422 alike, is
 * the API not giving the data: from the screen there is nothing to tell apart.
 */
function failureFor(status: number): ReadFailure {
  if (status === 401 || status === 403) return 'unauthorized'
  if (status === 404) return 'missing'
  return 'unavailable'
}

/**
 * Reading the API from a Server Component, with the reason it did not answer.
 *
 * The browser never talks to the backend directly — that is what
 * `app/api/proxy` is for — but a Server Component is already on the server and
 * holds the session cookie, so it calls the API itself and ships rendered HTML.
 * One fewer round trip, and the token never leaves the server.
 */
export async function readFromApi<T>(path: string): Promise<ApiRead<T>> {
  const token = (await cookies()).get('access_token')?.value
  // No cookie is not the API refusing: nobody asked it anything. It reads as a
  // refusal because that is what it means for the person — the private layout
  // has already sent a session-less visitor to the login.
  if (!token) return { ok: false, failure: 'unauthorized', status: null }

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS)
  try {
    const response = await fetch(`${API_URL}${API_PREFIX}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
      signal: controller.signal,
    })
    if (!response.ok) {
      return { ok: false, failure: failureFor(response.status), status: response.status }
    }
    return { ok: true, data: (await response.json()) as T }
  } catch {
    // Unreachable, or slower than a person waits. Either way the backend said
    // nothing, which is not the same as saying no.
    return { ok: false, failure: 'unavailable', status: null }
  } finally {
    clearTimeout(timeout)
  }
}

/**
 * The same read, for a screen that has one answer for every empty outcome.
 *
 * It stays because most screens do not branch on the reason, and making them
 * spell out a union they never read would be noise. What it is *not* is a
 * second way to reach the API: it is `readFromApi` with the reason dropped, so
 * a screen that later has to tell a refusal from an outage changes which
 * reader it calls and nothing else.
 *
 * Dropping the reason is a decision, not a default. A screen that renders a
 * refusal — "no tenés permiso" — has to read `readFromApi`, because `null`
 * here is also what a timeout looks like.
 */
export async function fetchFromApi<T>(path: string): Promise<T | null> {
  const read = await readFromApi<T>(path)
  return read.ok ? read.data : null
}
