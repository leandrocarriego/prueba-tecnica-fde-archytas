import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { CalendarGrid } from '@/components/purchases/CalendarGrid'
import { NoPermission } from '@/components/common/NoPermission'
import { Day } from '@/components/ui/amount'
import { ErrorState } from '@/components/ui/state'
import { readFromApi } from '@/lib/api/server'
import { windowFor } from '@/lib/purchases/calendar'
import { canEdit } from '@/lib/auth/permissions'
import type { Calendar } from '@/lib/purchases/types'

export const metadata = {
  title: 'Calendario — Plataforma Cordillera',
}

interface CalendarParams {
  since?: string
  until?: string
  sin_recibo?: string
  saldadas?: string
}

interface PageProps {
  searchParams: Promise<CalendarParams>
}

/**
 * La misma pantalla con un recorte puesto o sacado, **sin perder el mes**.
 *
 * La ventana sale de lo que devolvió el backend y no de la URL: la primera
 * visita no trae `since` ni `until` —el backend decide el mes en curso (RF-04)—
 * y sin esto, poner un filtro ahí volvería a empezar de cero en otro mes.
 */
function hrefFor(
  calendar: Calendar,
  filters: CalendarParams,
  changes: Partial<CalendarParams>
): string {
  const next = { ...filters, since: calendar.since, until: calendar.until, ...changes }
  const query = new URLSearchParams()
  for (const [name, value] of Object.entries(next)) {
    if (value) query.set(name, value)
  }
  return `/calendario?${query.toString()}`
}

/** Un recorte de la vista, que se apaga con el mismo clic con que se puso. */
function Recorte({ label, on, href }: { label: string; on: boolean; href: string }) {
  return (
    <Link
      href={href}
      aria-pressed={on}
      className={
        on
          ? 'rounded-full border border-primary bg-primary px-3.5 py-1.5 text-xs font-semibold text-primary-foreground'
          : 'rounded-full border border-input bg-card px-3.5 py-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:bg-muted'
      }
    >
      {label}
    </Link>
  )
}

/**
 * El calendario de vencimientos (006).
 *
 * Se abre en el mes en curso —eso lo decide el backend cuando no se le pide una
 * ventana (RF-04)— y avanzar o retroceder es cambiar la ventana en la URL, así
 * que una pantalla vista se comparte tal como se está viendo.
 *
 * **Se actualiza sola** (RF-31 a RF-36): lo que otra persona cambia llega por
 * el canal en vivo que abre `CalendarGrid`, y la pantalla se vuelve a pedir al
 * servidor.
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
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Calendario</h1>
        <ErrorState title="No pudimos traer el calendario." />
      </div>
    )
  }

  const calendar = read.data

  return (
    <div className="space-y-4">
      {/*
        El título de la pantalla y la navegación entre ventanas. El **mes** no
        está acá: lo titula la tarjeta de abajo, junto al estado del canal y a
        quién más está mirando, que es donde la guía lo pone. Repetirlo arriba
        sería decir dos veces lo mismo con dos tipografías.

        Avanzar y retroceder de mes es RF-05. Los meses se calculan sobre la
        ventana que el backend devolvió, así que el «mes anterior» de una
        ventana de dos semanas es coherente con lo que se está mirando, y no
        con un mes que la pantalla supuso.
      */}
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Calendario</h1>
        <p className="text-sm text-muted-foreground">
          {calendar.items.length}{' '}
          {calendar.items.length === 1 ? 'vencimiento en la ventana' : 'vencimientos en la ventana'}
          {' · '}
          <Day value={calendar.since} /> a <Day value={calendar.until} />
        </p>
      </div>

      {/*
        Moverse de mes y recortar lo que se ve. Los dos recortes son
        **interruptores**: puesto se apaga, y llevan la ventana que se está
        mirando con ellos. Antes eran enlaces fijos a `/calendario?sin_recibo=1`,
        así que filtrar en octubre devolvía a septiembre sin decirlo, y para
        sacar el filtro había que borrarlo de la barra de direcciones.
      */}
      <nav
        aria-label="Mes y recortes del calendario"
        className="flex flex-wrap items-center gap-2 text-sm"
      >
        <Link className="text-link hover:underline" href={windowFor(calendar.since, -1, filters)}>
          « Mes anterior
        </Link>
        <Link className="px-1 text-link hover:underline" href="/calendario">
          Este mes
        </Link>
        <Link className="text-link hover:underline" href={windowFor(calendar.since, 1, filters)}>
          Mes siguiente »
        </Link>
        <span aria-hidden className="mx-1 h-4 w-px bg-border" />
        <Recorte
          label="Sólo sin recibo"
          on={Boolean(filters.sin_recibo)}
          href={hrefFor(calendar, filters, {
            sin_recibo: filters.sin_recibo ? undefined : '1',
          })}
        />
        <Recorte
          label="Esconder las saldadas"
          on={filters.saldadas === 'no'}
          href={hrefFor(calendar, filters, {
            saldadas: filters.saldadas === 'no' ? undefined : 'no',
          })}
        />
      </nav>

      <CalendarGrid
        calendar={calendar}
        canEdit={canEdit(session?.permissions ?? {}, 'CALENDAR')}
        viewerId={session?.user.id ?? null}
      />
    </div>
  )
}
