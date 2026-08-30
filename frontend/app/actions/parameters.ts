'use server'

import { revalidatePath } from 'next/cache'

import { callApi, type ActionResult } from '@/lib/api/write'
import type { Parameter } from '@/lib/operations/types'

/**
 * The owner changes a business parameter (RF-02).
 *
 * One key at a time even though the endpoint takes a set: the panel saves each
 * row on its own, so a value the backend refuses says which row was wrong
 * instead of failing the whole screen. The transaction is still all-or-nothing
 * on the backend's side, which is what matters when a caller does send several.
 *
 * The message on the way back is the backend's own: RF-06 promises the refusal
 * says between which values the number had to be, and rewriting it here would
 * be a second copy of the range.
 */
export async function saveParameter(
  key: string,
  value: string
): Promise<ActionResult<Parameter[]>> {
  const result = await callApi<Parameter[]>('/operations/parameters', {
    method: 'PUT',
    body: JSON.stringify({ items: [{ key, value }] }),
  })
  if (result.ok) {
    revalidatePath('/configuracion')
    // The two price-update parameters are read on that screen as well.
    revalidatePath('/precios')
  }
  return result
}
