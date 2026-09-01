'use server'

import { revalidatePath } from 'next/cache'

import { callApi, type ActionResult } from '@/lib/api/write'

/** Lo que contesta pedir una extracción a mano. */
interface SyncRequested {
  key: string
  job_run_id: number
}

/**
 * Traer una de las seis fuentes ahora, sin esperar al latido.
 *
 * Existía sólo para la lista de precios, y no por una decisión: fue la primera
 * que se construyó y las cinco que vinieron después engancharon nada más el
 * latido. La consecuencia práctica es que cuando algo faltaba en pantalla no
 * había forma de forzar la consulta y había que esperar hasta cuatro horas.
 *
 * Una fuente que ya está corriendo vuelve rechazada con el mensaje del backend,
 * no con uno inventado acá: es el mismo camino que usa el botón de `/precios`.
 */
export async function requestSync(key: string): Promise<ActionResult<SyncRequested>> {
  const result = await callApi<SyncRequested>(`/operations/syncs/${key}`, { method: 'POST' })
  if (result.ok) {
    revalidatePath('/configuracion/actualizaciones')
  }
  return result
}
