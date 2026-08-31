import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { CalendarGrid } from '@/components/purchases/CalendarGrid'
import { NoPermission } from '@/components/common/NoPermission'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import { day } from '@/lib/format'
import type { Calendar } from '@/lib/purchases/types'

export const metadata = {
  title: 'Calendario — Plataforma Cordillera',
}

interface PageProps {
  searchParams: Promise<{ since?: string; until?: string; sin_recibo?: string; saldadas?: string }>
}

/**
 * El calendario de vencimientos (006).
 *
 * Se abre en el mes en curso —eso lo decide el backend cuando no se le pide una
 * ventana (RF-04)— y avanzar o retroceder es cambiar la ventana en la URL, así
 * que una pantalla vista se comparte tal como se está viendo.
 *
 * **Lo que esta pantalla no hace todavía**: los cambios de otra persona no
 * aparecen solos (RF-31 a RF-36). Está anotado en el traspaso de la feature: el
 * canal en vivo es lo que queda de la H5, y hasta que exista, quien mira ve el
 * estado del momento en que cargó la pantalla.
 */
export default async function CalendarPage({ searchParams }: PageProps) {
  const filters = await searchParams
  const query = new URLSearchParams()
  if (filters.since) query.set('since', filters.since)
  if (filters.until) query.set('until', filters.until)
  if (filters.sin_recibo) query.set('without_receipt', 'true')
  if (filters.saldadas === 'no') query.set('hide_settled', 'true')

  const [calendar, session] = await Promise.all([
    fetchFromApi<Calendar>(`/calendar?${query.toString()}`),
    getSession(),
  ])

  if (calendar === null) {
    return <NoPermission what="el calendario de vencimientos" />
  }

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Calendario</h1>
        <p className="text-sm text-muted-foreground">
          Del {day(calendar.since)} al {day(calendar.until)} · {calendar.items.length} vencimientos.
        </p>
      </header>

      <nav className="flex flex-wrap gap-4 text-sm">
        <Link className="underline" href="/calendario">
          Este mes
        </Link>
        <Link className="underline" href="/calendario?sin_recibo=1">
          Sólo sin recibo
        </Link>
        <Link className="underline" href="/calendario?saldadas=no">
          Esconder las saldadas
        </Link>
      </nav>

      <CalendarGrid calendar={calendar} canEdit={canEdit(session?.permissions ?? {}, 'CALENDAR')} />
    </main>
  )
}
