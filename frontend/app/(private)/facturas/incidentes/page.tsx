import Link from 'next/link'

import { IncidentList } from '@/components/purchases/IncidentList'
import { NoPermission } from '@/components/common/NoPermission'
import { readFromApi } from '@/lib/api/server'
import type { Incident } from '@/lib/purchases/types'
import { ErrorState } from '@/components/ui/state'

export const metadata = {
  title: 'Incidentes de recibo — Plataforma Cordillera',
}

/**
 * Las facturas que se pasaron de fecha sin su recibo de recepción (H10 de 005).
 *
 * El relevamiento contó 17 el primer día, y hasta ahora no había dónde verlas:
 * el backend abría el incidente todas las noches, `GET /receipt-incidents` lo
 * contestaba y la Server Action de cerrarlo estaba escrita contra esta ruta,
 * que no existía.
 *
 * Lo que se puede hacer acá es **cerrar el incidente explicando qué se hizo**,
 * y eso es todo: emitir el recibo sigue estando negado, porque la fecha ya
 * pasó y nada la reabre — ni cerrar el incidente, ni reprogramar después. Un
 * incidente cerrado no se borra ni se apaga: deja de contarse entre los
 * pendientes y se sigue pudiendo consultar, con su motivo y con quién lo cerró.
 */
export default async function IncidentsPage() {
  const read = await readFromApi<Incident[]>('/receipt-incidents')

  if (!read.ok) {
    if (read.failure === 'unauthorized') {
      return <NoPermission what="los recibos de recepción" />
    }
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Incidentes de recibo</h1>
        <ErrorState title="No pudimos traer los incidentes.">
          Probá de nuevo en unos minutos.
        </ErrorState>
      </div>
    )
  }

  const incidents = read.data
  const open = incidents.filter(incident => incident.closed_at === null)
  const closed = incidents.filter(incident => incident.closed_at !== null)

  return (
    <div className="space-y-8">
      <Link className="text-sm text-link hover:underline" href="/facturas">
        « Volver a las facturas
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Incidentes de recibo</h1>
        <p className="text-sm text-muted-foreground">
          {open.length === 0
            ? 'No hay ninguna factura vencida sin su recibo.'
            : `${open.length} ${open.length === 1 ? 'factura se pasó' : 'facturas se pasaron'} de fecha sin su recibo de recepción.`}
        </p>
        <p className="text-sm text-muted-foreground">
          Pasada la fecha de vencimiento ya no corresponde emitir el recibo, y cerrar el incidente
          tampoco lo habilita: lo que se registra acá es qué se hizo al respecto.
        </p>
      </header>

      <IncidentList incidents={open} />

      {closed.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-medium">Cerrados</h2>
          <p className="text-sm text-muted-foreground">
            Dejaron de contarse entre los pendientes y se siguen pudiendo consultar.
          </p>
          <IncidentList incidents={closed} />
        </section>
      )}
    </div>
  )
}
