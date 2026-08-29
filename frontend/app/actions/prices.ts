'use server'

import { revalidatePath } from 'next/cache'
import { cookies } from 'next/headers'

import type { JobRun, PriceUpdateSettings } from '@/lib/catalog/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_PREFIX = '/api/v1'

/** What every one of these actions answers: it worked, or why it did not. */
export type ActionResult<T> = { ok: true; data: T } | { ok: false; message: string }

/** The envelope every failing endpoint returns: see `app.main` in the backend. */
interface ApiErrorBody {
  error?: { type?: string; message?: string; details?: Record<string, unknown> }
}

const UNREACHABLE = 'No se pudo contactar al servidor'
const NO_SESSION = 'La sesión expiró. Iniciá sesión de nuevo'

async function call<T>(path: string, init: RequestInit): Promise<ActionResult<T>> {
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
    if (!response.ok) {
      return { ok: false, message: body.error?.message ?? UNREACHABLE }
    }
    return { ok: true, data: body }
  } catch {
    return { ok: false, message: UNREACHABLE }
  }
}

/**
 * Ask the portal for the list right now (RF-14).
 *
 * A 409 is not an error to hide: it means somebody else's update is already
 * running, and RF-15 says the person is told instead of a second one starting.
 */
export async function requestPriceUpdate(): Promise<ActionResult<{ job_run_id: number }>> {
  const result = await call<{ job_run_id: number }>('/price-updates', { method: 'POST' })
  if (result.ok) revalidatePath('/precios')
  return result
}

/** How that run ended, so whoever asked finds out either way (RF-16). */
export async function readPriceUpdate(jobRunId: number): Promise<ActionResult<JobRun>> {
  return call<JobRun>(`/price-updates/${jobRunId}`, { method: 'GET' })
}

/** The owner changes how often, and what counts as a big rise (RF-18, RF-19). */
export async function savePriceUpdateSettings(
  intervalHours: number,
  highlightThresholdPct: number
): Promise<ActionResult<PriceUpdateSettings>> {
  const result = await call<PriceUpdateSettings>('/price-updates/settings', {
    method: 'PUT',
    body: JSON.stringify({
      interval_hours: intervalHours,
      highlight_threshold_pct: highlightThresholdPct,
    }),
  })
  if (result.ok) {
    revalidatePath('/precios')
    revalidatePath('/precios/configuracion')
  }
  return result
}
