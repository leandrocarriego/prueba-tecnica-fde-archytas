import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { AuditTable } from '@/components/operations/AuditTable'
import { readFromApi } from '@/lib/api/server'
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
  pagina?: string
}

/**
 * Which page of the log is being asked for, from the address bar and sanitised.
 *
 * A number and not an offset, because the address bar is read by people: what
 * `?pagina=2` means is plain, and what `?skip=50` means depends on knowing how
 * many rows fit on a page. The offset is arithmetic done here, once.
 */
function pageFrom(value: string | undefined): number {
  const parsed = Number.parseInt(value ?? '', 10)
  return Number.isFinite(parsed) && parsed > 1 ? parsed : 1
}

/** The query string the API is asked for, built only from filters that were set. */
function queryFor({ persona, desde, hasta }: SearchParams, skip: number): string {
  const query = new URLSearchParams({ limit: String(PAGE_SIZE) })
  if (skip > 0) query.set('skip', String(skip))
  if (persona) query.set('actor_user_id', persona)
  // A day, as typed in the filter, means the whole day: from its first instant
  // to its last. Sending the bare date would ask for everything up to midnight
  // and silently drop the changes made during the day somebody asked about.
  if (desde) query.set('since', `${desde}T00:00:00`)
  if (hasta) query.set('until', `${hasta}T23:59:59`)
  return query.toString()
}

/** The same screen one page away: the filters travel, only the number moves. */
function pageHref({ persona, desde, hasta }: SearchParams, page: number): string {
  const query = new URLSearchParams()
  if (desde) query.set('desde', desde)
  if (hasta) query.set('hasta', hasta)
  if (persona) query.set('persona', persona)
  if (page > 1) query.set('pagina', String(page))
  const suffix = query.toString()
  return suffix ? `/historial?${suffix}` : '/historial'
}

/**
 * The un-paginated answer, read as the single page it is.
 *
 * The history of one datum is bounded by the datum, so the API answers it as a
 * plain list. The screen reads one shape.
 */
function asPage(items: AuditEntry[]): AuditEntryList {
  return { items, total: items.length, skip: 0, limit: items.length }
}

/**
 * How much of the log is on screen, in words.
 *
 * It exists because the log is append-only and grows forever: somebody who
 * filters, does not find what they are looking for and is shown fifty rows has
 * no way of telling "it did not happen" from "it is on row fifty-one".
 */
function countLabel(page: AuditEntryList): string {
  const first = page.skip + 1
  const last = page.skip + page.items.length
  if (page.skip === 0 && last === page.total) {
    return page.total === 1 ? '1 cambio.' : `${page.total} cambios.`
  }
  return `Mostrando ${first}–${last} de ${page.total} cambios.`
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
  const current = ofOneDatum ? 1 : pageFrom(filters.pagina)
  const skip = (current - 1) * PAGE_SIZE

  // Only the owner reaches `/users`, so a refusal there is the answer "no sos
  // el dueño" and the filter offers what this person can actually ask for:
  // their own changes. Anything else is the API failing, and the read below
  // fails with it — the screen says so once, in one place, instead of quietly
  // shrinking the filter over an outage.
  const people = ofOneDatum ? null : await readFromApi<UserList>('/users?limit=100')
  const roster = people !== null && people.ok ? people.data.items : null

  const read = ofOneDatum
    ? await readFromApi<AuditEntry[]>(`/operations/audit/${filters.entidad}/${filters.id}`)
    : await readFromApi<AuditEntryList>(`/operations/audit?${queryFor(filters, skip)}`)
  const page = read.ok ? (Array.isArray(read.data) ? asPage(read.data) : read.data) : null

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
          can send to somebody else. It carries no offset on purpose — filtering
          again starts at the first row, which is where the answer to a new
          question is.
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
              {roster
                ? roster.map(person => (
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

      {page === null ? (
        <p className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-900">
          No pudimos traer el historial. Probá de nuevo en unos minutos.
        </p>
      ) : (
        <>
          {page.items.length > 0 && (
            <p className="text-sm text-muted-foreground">{countLabel(page)}</p>
          )}
          <AuditTable items={page.items} />
          {!ofOneDatum && (current > 1 || page.skip + page.items.length < page.total) && (
            <nav className="flex items-center gap-4 text-sm">
              {current > 1 && (
                <Link
                  className="underline underline-offset-2"
                  href={pageHref(filters, current - 1)}
                >
                  « Más nuevos
                </Link>
              )}
              {page.skip + page.items.length < page.total && (
                <Link
                  className="underline underline-offset-2"
                  href={pageHref(filters, current + 1)}
                >
                  Más viejos »
                </Link>
              )}
            </nav>
          )}
        </>
      )}
    </main>
  )
}
