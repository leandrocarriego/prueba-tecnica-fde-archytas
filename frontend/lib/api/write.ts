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

interface ApiErrorBody {
  error?: { type?: string; message?: string; details?: Record<string, unknown> }
}

/** Send a request with the caller's session, and bring back either side of it. */
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

    const body = (await response.json()) as T & ApiErrorBody
    if (!response.ok) return { ok: false, message: body.error?.message ?? UNREACHABLE }
    return { ok: true, data: body }
  } catch {
    return { ok: false, message: UNREACHABLE }
  }
}
