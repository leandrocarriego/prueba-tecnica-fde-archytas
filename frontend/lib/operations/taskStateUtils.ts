/** Display helpers for the job run states exposed by the operations module. */

import type { JobStatus } from '@/lib/operations/types'

const LABELS: Record<JobStatus, string> = {
  PENDING: 'Pendiente',
  RUNNING: 'En proceso',
  SUCCEEDED: 'Completado',
  FAILED: 'Falló',
}

const COLORS: Record<JobStatus, string> = {
  PENDING: 'text-slate-500',
  RUNNING: 'text-blue-600',
  SUCCEEDED: 'text-emerald-600',
  FAILED: 'text-red-600',
}

/** Spanish label for a run state, falling back to the raw value. */
export function getJobStatusLabel(status: JobStatus | string): string {
  return LABELS[status as JobStatus] ?? status
}

/** Tailwind text colour for a run state. */
export function getJobStatusColor(status: JobStatus | string): string {
  return COLORS[status as JobStatus] ?? 'text-slate-500'
}
