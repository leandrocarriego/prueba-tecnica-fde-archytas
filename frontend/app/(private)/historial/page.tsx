import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { AuditTable } from '@/components/operations/AuditTable'
import { fetchFromApi } from '@/lib/api/server'
import type { components } from '@/lib/api/types'
import type { AuditEntry, AuditEntryList } from '@/lib/operations/types'

type UserList = components['schemas']['UserList']

export const metadata = {
  title: 'Historial de cambios — Plataforma Cordillera',
}

const PAGE_SIZE = 50

interface SearchParams {
  persona?: string
  desde?: string
  hasta?: string
  entidad?: string
  id?: string
}

/** The query string the API is asked for, built only from filters that were set. */
function queryFor({ persona, desde, hasta }: SearchParams): string {
  const query = new URLSearchParams({ limit: String(PAGE_SIZE) })
  if (persona) query.set('actor_user_id', persona)
  // A day, as typed in the filter, means the whole day: from its first instant
  // to its last. Sending the bare date would ask for everything up to midnight
  // and silently drop the changes made during the day somebody asked about.
  if (desde) query.set('since', `${desde}T00:00:00`)
  if (hasta) query.set('until', `${hasta}T23:59:59`)
  return query.toString()
}

/**
 * Every manual change, and who made it (H2).
 *
 * Two shapes on one screen, because they are the same question at two zoom
 * levels. Without `entidad` it is the whole log, filterable by person and by
 * date range (RF-13, RF-14). With it, the history of a single datum — which is
 * what a corrected value links to, so its story is reachable without going
 * looking for it (RF-15).
 *
 * There is no filter for "section", and that is not an omission: the backend
 * narrows the log to the sections the caller reaches (RF-18, RF-19), so the
 * owner sees the three people and everybody else sees their own without the
 * screen deciding anything.
 */
export default async function HistoryPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>
}) {
  const filters = await searchParams
  const session = await getSession()
  const ofOneDatum = Boolean(filters.entidad && filters.id)

  // Only the owner reaches `/users`, so for anybody else this is `null` and
  // the filter offers what they can actually ask for: their own changes. The
  // refusal is the backend's either way — this only decides what to draw.
  const people = ofOneDatum ? null : await fetchFromApi<UserList>('/users?limit=100')

  const entries = ofOneDatum
    ? await fetchFromApi<AuditEntry[]>(`/operations/audit/${filters.entidad}/${filters.id}`)
    : (await fetchFromApi<AuditEntryList>(`/operations/audit?${queryFor(filters)}`))?.items

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Historial de cambios</h1>
        <p className="text-sm text-muted-foreground">
          Todo lo que alguien cargó o corrigió a mano, de lo más nuevo a lo más viejo. No se puede
          editar ni borrar.
        </p>
      </header>

      {ofOneDatum ? (
        <p className="text-sm">
          Mostrando sólo los cambios de un dato.{' '}
          <Link className="underline underline-offset-2" href="/historial">
            Ver todo el historial
          </Link>
        </p>
      ) : (
        /*
          A plain GET form, so the filters live in the address bar: the page
          stays a Server Component, and a filtered history is a link somebody
          can send to somebody else.
        */
        <form className="flex flex-wrap items-end gap-4 rounded border p-4" method="get">
          <div className="space-y-1">
            <label className="block text-sm font-medium" htmlFor="desde">
              Desde
            </label>
            <input
              className="rounded border px-3 py-2 text-sm"
              id="desde"
              name="desde"
              type="date"
              defaultValue={filters.desde ?? ''}
            />
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium" htmlFor="hasta">
              Hasta
            </label>
            <input
              className="rounded border px-3 py-2 text-sm"
              id="hasta"
              name="hasta"
              type="date"
              defaultValue={filters.hasta ?? ''}
            />
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium" htmlFor="persona">
              Persona
            </label>
            <select
              className="rounded border px-3 py-2 text-sm"
              id="persona"
              name="persona"
              defaultValue={filters.persona ?? ''}
            >
              <option value="">Todas</option>
              {people
                ? people.items.map(person => (
                    <option key={person.id} value={String(person.id)}>
                      {person.name}
                      {person.last_name ? ` ${person.last_name}` : ''}
                    </option>
                  ))
                : session && <option value={String(session.user.id)}>Sólo mis cambios</option>}
            </select>
          </div>
          <button className="rounded border px-4 py-2 text-sm hover:bg-gray-50" type="submit">
            Filtrar
          </button>
          {(filters.desde || filters.hasta || filters.persona) && (
            <Link className="text-sm text-muted-foreground underline" href="/historial">
              Limpiar
            </Link>
          )}
        </form>
      )}

      {entries === undefined || entries === null ? (
        <p className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-900">
          No pudimos traer el historial. Probá de nuevo en unos minutos.
        </p>
      ) : (
        <AuditTable items={entries} />
      )}
    </main>
  )
}
