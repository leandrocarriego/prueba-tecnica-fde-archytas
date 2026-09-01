/** Display helpers for the job run states exposed by the operations module. */

import type { JobStatus } from '@/lib/operations/types'

const LABELS: Record<JobStatus, string> = {
  PENDING: 'Pendiente',
  RUNNING: 'En proceso',
  SUCCEEDED: 'Completado',
  FAILED: 'Falló',
}

/** Spanish label for a run state, falling back to the raw value. */
export function getJobStatusLabel(status: JobStatus | string): string {
  return LABELS[status as JobStatus] ?? status
}

/*
 * Acá había un `getJobStatusColor`, que era una **segunda** tabla de colores de
 * estado: el mapa de la plataforma es `lib/ui/tone.ts`, y dos tablas de lo
 * mismo terminan discrepando. La corrida ahora se dibuja con `<Badge>` y el
 * tono que sale de ahí.
 */
