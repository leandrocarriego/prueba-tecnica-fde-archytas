import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { CalendarGrid } from '@/components/purchases/CalendarGrid'
import { NoPermission } from '@/components/common/NoPermission'
import { readFromApi } from '@/lib/api/server'
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

  const [read, session] = await Promise.all([
    readFromApi<Calendar>(`/calendar?${query.toString()}`),
    getSession(),
  ])

  // Una negativa y una caída no son lo mismo: con la API caída, decirle al
  // dueño «no tenés permiso, pedíselo al dueño» es un consejo sobre el que
  // nadie puede actuar, sobre un permiso que nunca le faltó.
  if (!read.ok) {
    if (read.failure === 'unauthorized') {
      return <NoPermission what="el calendario de vencimientos" />
    }
    return (
      <main className="mx-auto max-w-4xl space-y-4 p-8">
        <h1 className="text-2xl font-bold">Calendario</h1>
        <p className="rounded border border-danger-border bg-danger-surface p-4 text-sm text-danger">
          No pudimos traer el calendario. Probá de nuevo en unos minutos.
        </p>
      </main>
    )
  }

  const calendar = read.data

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Calendario</h1>
        <p className="text-sm text-muted-foreground">
          Del {day(calendar.since)} al {day(calendar.until)} · {calendar.items.length} vencimientos.
        </p>
      </header>

      {/*
        Avanzar y retroceder de mes (RF-05). Los meses se calculan sobre la
        ventana que el backend devolvió, así que el «mes anterior» de una
        ventana de dos semanas es coherente con lo que se está mirando, y no
        con un mes que la pantalla supuso.
      */}
      <nav className="flex flex-wrap items-center gap-4 text-sm">
        <Link className="underline" href={windowFor(calendar.since, -1, filters)}>
          « Mes anterior
        </Link>
        <Link className="underline" href="/calendario">
          Este mes
        </Link>
        <Link className="underline" href={windowFor(calendar.since, 1, filters)}>
          Mes siguiente »
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

/** La URL del mes anterior o el siguiente, conservando los filtros puestos. */
function windowFor(since: string, offset: number, filters: Record<string, string | undefined>) {
  const [year, month] = since.split('-').map(Number)
  const first = new Date(Date.UTC(year, month - 1 + offset, 1))
  const last = new Date(Date.UTC(year, month + offset, 0))
  const iso = (date: Date) => date.toISOString().slice(0, 10)
  const query = new URLSearchParams({ since: iso(first), until: iso(last) })
  if (filters.sin_recibo) query.set('sin_recibo', filters.sin_recibo)
  if (filters.saldadas) query.set('saldadas', filters.saldadas)
  return `/calendario?${query.toString()}`
}
