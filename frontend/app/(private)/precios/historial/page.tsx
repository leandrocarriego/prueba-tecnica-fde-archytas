import Link from 'next/link'

import { formatMoment } from '@/lib/catalog/format'
import { fetchFromApi } from '@/lib/api/server'
import type { components } from '@/lib/api/types'
import { Badge } from '@/components/ui/badge'
import { Empty, ErrorState } from '@/components/ui/state'

type JobRunList = components['schemas']['JobRunList']
type JobRun = components['schemas']['JobRunRead']
type JobStatus = components['schemas']['JobStatus']

/** The task that visits the portal and brings the price list (portal module). */
const PRICE_TASK = 'portal.extract_price_list'

export const metadata = {
  title: 'Historial de sync — Plataforma Cordillera',
}

/**
 * El historial de sincronizaciones de precios (guía visual `3k`).
 *
 * Cada corrida contra el portal como un hecho: cuándo terminó, cómo terminó y
 * cuántas filas dejó apartadas. Sale de `/operations/jobs`, filtrado por la task
 * que trae la lista; no hay número inventado, y cuando todavía no corrió
 * ninguna, lo dice.
 */
export default async function SyncHistoryPage() {
  const runs = await fetchFromApi<JobRunList>(
    `/operations/jobs?task_name=${PRICE_TASK}&limit=50`
  )

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <Link className="text-sm text-link hover:underline" href="/precios">
          ← Volver a la lista de precios
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Historial de sync</h1>
        <p className="text-sm text-muted-foreground">
          Cada consulta al portal, cuándo terminó y qué dejó apartado.
        </p>
      </header>

      {runs === null ? (
        <ErrorState title="No pudimos traer el historial.">
          Probá de nuevo en unos minutos.
        </ErrorState>
      ) : runs.items.length === 0 ? (
        <Empty title="Todavía no corrió ninguna sincronización.">
          Cuando el portal se consulte —sola de madrugada o desde «Actualizar ahora»— cada corrida
          aparece acá.
        </Empty>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-card">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted">
                <th className="section-label px-4 py-2.5 text-left">Cuándo</th>
                <th className="section-label px-4 py-2.5 text-left">Resultado</th>
                <th className="section-label px-4 py-2.5 text-right">Apartadas</th>
              </tr>
            </thead>
            <tbody>
              {runs.items.map(run => (
                <tr key={run.id} className="border-b border-border">
                  <td className="amount px-4 py-3 text-sm text-foreground">
                    {formatMoment(run.finished_at ?? run.started_at)}
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={STATUS_TONE[run.status]}>{STATUS_LABEL[run.status]}</Badge>
                    {run.error && (
                      <span className="ml-2 text-xs text-muted-foreground">{run.error}</span>
                    )}
                  </td>
                  <td className="amount px-4 py-3 text-right text-sm text-muted-ink">
                    {quarantinedOf(run)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

const STATUS_TONE: Record<JobStatus, 'ok' | 'danger' | 'info' | 'neutral'> = {
  SUCCEEDED: 'ok',
  FAILED: 'danger',
  RUNNING: 'info',
  PENDING: 'neutral',
}

const STATUS_LABEL: Record<JobStatus, string> = {
  SUCCEEDED: 'Al día',
  FAILED: 'Falló',
  RUNNING: 'En curso',
  PENDING: 'En cola',
}

/** How many rows the run set aside, when it reported it. */
function quarantinedOf(run: JobRun): string {
  const value = (run.result ?? {})['quarantined']
  return typeof value === 'number' ? String(value) : '—'
}
