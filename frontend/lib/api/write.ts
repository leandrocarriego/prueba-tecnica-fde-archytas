/**
 * Writing to the API from a Server Action.
 *
 * `lib/api/server.ts` is the read side and answers `null` on any failure,
 * which is right for a page that renders an empty state. A write cannot do
 * that: RF-22 says whoever ran an action finds out whether it was applied or
 * why it was not, so the message the backend sent has to survive the trip.
 *
 * The error envelope is the one `app.main` builds for every failure, so a
 * refused parameter arrives here already saying between which values it had to
 * be (RF-06).
 */
import { cookies } from 'next/headers'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_PREFIX = '/api/v1'

const UNREACHABLE = 'No se pudo contactar al servidor'
const NO_SESSION = 'La sesión expiró. Iniciá sesión de nuevo'

/** What every action answers: it worked, or why it did not. */
export type ActionResult<T> = { ok: true; data: T } | { ok: false; message: string }

/** An object whose keys can be asked about, told apart from `null` and the rest. */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

/**
 * The message inside the envelope `app.main` builds — `{ error: { message } }`.
 *
 * Asked, not asserted. A body comes off `response.json()` as `unknown`, and not
 * every failure that reaches here was written by our own error handler: a proxy
 * in front of the API answers 502 with a body of its own shape. Declaring the
 * envelope promised the compiler a `message: string` that nothing ever checked,
 * so a `message` that was not a string — a number, an object — travelled as one
 * inside `ActionResult` and reached the screen that renders it. Asked, it falls
 * to `UNREACHABLE` like any other body we did not write. Three comparisons cost
 * nothing and cannot be wrong.
 */
function refusalMessage(body: unknown): string | null {
  if (!isRecord(body)) return null
  const error = body.error
  if (!isRecord(error)) return null
  return typeof error.message === 'string' ? error.message : null
}

/**
 * Send a request with the caller's session, and bring back either side of it.
 *
 * The two `as T` below are the only promises in this file the compiler is
 * asked to take on trust, and they are the same one: `T` is named by the
 * caller from the generated schema (`TS-05`), so the body is checked against
 * the backend's contract when those types are regenerated, never at runtime.
 * A caller that names a `T` other than `void` is also promising the endpoint
 * does not answer 204 — the empty body has no value to give it.
 */
export async function callApi<T>(path: string, init: RequestInit): Promise<ActionResult<T>> {
  const token = (await cookies()).get('access_token')?.value
  if (!token) return { ok: false, message: NO_SESSION }

  try {
    const response = await fetch(`${API_URL}${API_PREFIX}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...(init.headers ?? {}),
      },
      cache: 'no-store',
    })

    if (response.status === 204) return { ok: true, data: undefined as T }

    const body: unknown = await response.json()
    if (!response.ok) return { ok: false, message: refusalMessage(body) ?? UNREACHABLE }
    return { ok: true, data: body as T }
  } catch {
    return { ok: false, message: UNREACHABLE }
  }
}
