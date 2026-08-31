'use server'

import { revalidatePath } from 'next/cache'

import { callApi, type ActionResult as ApiActionResult } from '@/lib/api/write'
import type { JobRun } from '@/lib/catalog/types'

/**
 * The answer shape, pointed at and no longer spelled out again.
 *
 * This file held the first copy of it, from before `lib/api/write` existed,
 * and five other action files import the name from here. An alias keeps that
 * import working while there is one description of the shape: two identical
 * type aliases are structurally compatible, so nothing would ever have told us
 * the day they stopped being identical.
 */
export type ActionResult<T> = ApiActionResult<T>

/**
 * Ask the portal for the list right now (RF-14).
 *
 * A 409 is not an error to hide: it means somebody else's update is already
 * running, and RF-15 says the person is told instead of a second one starting.
 * `callApi` brings back the sentence the backend wrote, which is the one the
 * button then shows.
 */
export async function requestPriceUpdate(): Promise<ActionResult<{ job_run_id: number }>> {
  const result = await callApi<{ job_run_id: number }>('/price-updates', { method: 'POST' })
  if (result.ok) revalidatePath('/precios')
  return result
}

/**
 * How that run ended, so whoever asked finds out either way (RF-16).
 *
 * A read, and still through `callApi` and not through the reader in
 * `lib/api/server` — which is a choice here, unlike in the POST above, because
 * the reader only does GETs and this is one. It answers a failure with a
 * reason of its own, three words a page can render, and drops whatever the
 * backend said. But this run is followed until it ends and the button shows
 * what comes back, so the backend's own sentence has to survive the trip.
 */
export async function readPriceUpdate(jobRunId: number): Promise<ActionResult<JobRun>> {
  return callApi<JobRun>(`/price-updates/${jobRunId}`, { method: 'GET' })
}
