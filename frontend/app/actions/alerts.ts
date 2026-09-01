'use server'

import { revalidatePath } from 'next/cache'

import { callApi, type ActionResult } from '@/lib/api/write'
import type { AlertKind, AlertRoute, AlertTested } from '@/lib/notifications/types'

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
    revalidatePath('/configuracion/notificaciones')
  }
  return result
}

/**
 * Mandar un aviso de prueba de un tipo, a quien lo recibiría de verdad.
 *
 * **No revalida nada**: no cambia ningún dato, manda un WhatsApp. Lo que la
 * pantalla hace con la respuesta es decir a cuántos teléfonos salió, que es la
 * mitad que se puede afirmar sin esperar al worker.
 */
export async function testAlertRoute(kind: AlertKind): Promise<ActionResult<AlertTested>> {
  return callApi<AlertTested>(`/alerts/routes/${kind}/test`, { method: 'POST' })
}
