'use server'

import { revalidatePath } from 'next/cache'

import { callApi, type ActionResult } from '@/lib/api/write'
import type { AlertKind, AlertRoute } from '@/lib/notifications/types'

/**
 * El dueño decide quién recibe un tipo de aviso (RF-37 de 007).
 *
 * Un tipo por vez, como los parámetros del sistema de al lado: si el backend
 * rechaza uno, la pantalla dice cuál y no falla entera.
 */
export async function setAlertRoute(
  kind: AlertKind,
  role: string
): Promise<ActionResult<AlertRoute>> {
  const result = await callApi<AlertRoute>(`/alerts/routes/${kind}`, {
    method: 'PUT',
    body: JSON.stringify({ role }),
  })
  if (result.ok) {
    revalidatePath('/configuracion')
  }
  return result
}
