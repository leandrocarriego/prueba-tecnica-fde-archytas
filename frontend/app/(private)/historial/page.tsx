import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { AuditTable } from '@/components/operations/AuditTable'
import { readFromApi } from '@/lib/api/server'
import type { components } from '@/lib/api/types'
import { canEdit } from '@/lib/auth/permissions'
import { standingCorrections } from '@/lib/catalog/corrections'
import type { CorrectionInForce } from '@/lib/catalog/types'
import { isKnownEntityType } from '@/lib/operations/audit'
import type { AuditEntry, AuditEntryList } from '@/lib/operations/types'
import { ErrorState } from '@/components/ui/state'
import { Button } from '@/components/ui/button'
import { Input, selectClassName } from '@/components/ui/input'
import { Notice } from '@/components/ui/notice'

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
 * An origin nobody dials, for resolving a path the way `fetch` is about to.
 *
 * The real one lives in `lib/api/server` and is of no consequence here: a URL
 * is parsed the same way whatever it points at, and it is only the parsing
 * this file needs to see.
 */
const RESOLUTION_ORIGIN = 'http://api.invalid'

/**
 * The API path for the history of one datum, or nothing if there is no such
 * datum to ask about.
 *
 * Both halves arrive from the address bar, so both are text somebody can type,
 * and neither used to be treated as such: interpolated straight into the path,
 * a value carrying `../`, `?` or `#` rewrites the URL and sends this request —
 * with the session of whoever is reading — at a different endpoint of the API.
 *
 * So each half is closed in the way its own shape allows. The kind is matched
 * against the ones this screen can name (`isKnownEntityType`), because a kind
 * it has no word for is a link it cannot answer, not a question worth asking.
 * The identifier cannot be matched — each module writes it in its own shape, a
 * product id here and a parameter key there — so it is escaped, and then the
 * path it produced is resolved and compared with the one that was meant.
 *
 * That second step is not belt and braces: escaping alone does not close this.
 * `.` and `..` are unreserved characters and come back from
 * `encodeURIComponent` unchanged, and the URL parser collapses them while
 * building the request — `?id=..` leaves for the listing endpoint, and the
 * whole log comes back and is rendered under «Mostrando sólo los cambios de un
 * dato». Comparing says it in one line, without this function having to keep a
 * list of the spellings that mean "go up".
 */
function auditPathFor({ entidad, id }: SearchParams): string | null {
  if (!entidad || !id || !isKnownEntityType(entidad)) return null
  const path = `/operations/audit/${encodeURIComponent(entidad)}/${encodeURIComponent(id)}`
  return new URL(path, RESOLUTION_ORIGIN).pathname === path ? path : null
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

// The data of this module whose corrections `catalog` keeps, and whose
// `entity_id` is a product id. A kind outside this set is a datum of some other
// module, whose corrections live in a table of its own: asking `catalog` about
// it would be asking the wrong module, so the log simply makes no offer over
// that row until the feature that owns it brings its own answer.
const CORRECTABLE_KINDS = new Set(['catalog.product', 'catalog.product_price'])

/**
 * Which correction still stands on each row of this page, or `null` if the
 * answer never came back.
 *
 * One question for the whole page: the rows name at most fifty products, and
 * asking per row would be fifty requests to build one column. `null` and an
 * empty map are deliberately different — an empty map is "nothing here is
 * undoable", which is the truth for a log of loads and parameter changes, and
 * `null` is "we could not find out", which the screen says out loud instead of
 * quietly withdrawing an offer the person had every right to (the same rule
 * that keeps a backend being down from reading as a permission being missing).
 */
async function undoableIn(items: AuditEntry[]): Promise<Map<string, number> | null> {
  const products = new Set<number>()
  for (const entry of items) {
    if (!CORRECTABLE_KINDS.has(entry.entity_type)) continue
    const id = Number.parseInt(entry.entity_id, 10)
    if (Number.isSafeInteger(id)) products.add(id)
  }
  if (products.size === 0) return new Map()

  const query = [...products].map(id => `product_id=${id}`).join('&')
  const read = await readFromApi<CorrectionInForce[]>(`/catalog/corrections?${query}`)
  return read.ok ? standingCorrections(read.data) : null
}

/** The heading, which every shape of this screen carries. */
function Header() {
  return (
    <header className="space-y-1">
      <h1 className="text-2xl font-bold">Historial de cambios</h1>
      <p className="text-sm text-muted-foreground">
        Todo lo que alguien cargó o corrigió a mano, de lo más nuevo a lo más viejo. No se puede
        editar ni borrar.
      </p>
    </header>
  )
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
  const ofOneDatum = Boolean(filters.entidad && filters.id)
  const datumPath = auditPathFor(filters)

  // One datum was asked for and the link cannot be answered: either the kind is
  // not one this screen names, or the identifier would not stay a single path
  // segment. Neither is an outage nor a history with nothing in it, and showing
  // the whole log instead would answer a question nobody asked. Said before
  // anything reaches the API, because there is nothing to ask it.
  if (ofOneDatum && datumPath === null) {
    return (
      <div className="space-y-6">
        <Header />
        <Notice
          tone="warn"
          title="El enlace pide el historial de un dato que esta pantalla no conoce."
          action={
            <Button asChild variant="outline">
              <Link href="/historial">Ver todo el historial</Link>
            </Button>
          }
        />
      </div>
    )
  }

  const session = await getSession()
  const current = ofOneDatum ? 1 : pageFrom(filters.pagina)
  const skip = (current - 1) * PAGE_SIZE

  // Only the owner reaches `/users`, so a refusal there is the answer "no sos
  // el dueño" and the filter offers what this person can actually ask for:
  // their own changes. Anything else is the API failing, and the read below
  // fails with it — the screen says so once, in one place, instead of quietly
  // shrinking the filter over an outage.
  const people = ofOneDatum ? null : await readFromApi<UserList>('/users?limit=100')
  const roster = people !== null && people.ok ? people.data.items : null

  const read = datumPath
    ? await readFromApi<AuditEntry[]>(datumPath)
    : await readFromApi<AuditEntryList>(`/operations/audit?${queryFor(filters, skip)}`)
  const page = read.ok ? (Array.isArray(read.data) ? asPage(read.data) : read.data) : null

  // Undoing a correction is the owner's alone (RF-30), and its acceptance
  // criterion puts it on this screen. Asked for only when it is going to be
  // offered: the route refuses anybody else, so for the other two roles this
  // would be a round trip that can only answer 403.
  const mayUndo = session !== null && canEdit(session.permissions, 'MANUAL_CORRECTIONS')
  const undoable =
    mayUndo && page !== null ? await undoableIn(page.items) : new Map<string, number>()

  return (
    <div className="space-y-6">
      <Header />

      {ofOneDatum ? (
        <p className="text-sm">
          Mostrando sólo los cambios de un dato.{' '}
          <Link className="text-link hover:underline" href="/historial">
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
        <form
          className="flex flex-wrap items-end gap-4 rounded-lg border border-border bg-card p-4"
          method="get"
        >
          <div className="space-y-1">
            <label className="block text-sm font-medium" htmlFor="desde">
              Desde
            </label>
            <Input id="desde" name="desde" type="date" defaultValue={filters.desde ?? ''} />
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium" htmlFor="hasta">
              Hasta
            </label>
            <Input id="hasta" name="hasta" type="date" defaultValue={filters.hasta ?? ''} />
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium" htmlFor="persona">
              Persona
            </label>
            <select
              className={selectClassName}
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
          {/* Filtrar no es la tarea: leer el historial lo es (`RF-11`). */}
          <Button type="submit" variant="outline">
            Filtrar
          </Button>
          {(filters.desde || filters.hasta || filters.persona) && (
            <Link className="text-sm text-link hover:underline" href="/historial">
              Limpiar
            </Link>
          )}
        </form>
      )}

      {page === null ? (
        <ErrorState title="No pudimos traer el historial.">
          Probá de nuevo en unos minutos.
        </ErrorState>
      ) : (
        <>
          {page.items.length > 0 && (
            <p className="text-sm text-muted-foreground">{countLabel(page)}</p>
          )}
          {undoable === null && (
            <Notice tone="warn" title="No pudimos traer las correcciones que se pueden deshacer.">
              El historial es el de siempre; para deshacer una corrección, entrá al dato o probá de
              nuevo en unos minutos.
            </Notice>
          )}
          <AuditTable items={page.items} undoable={undoable ?? undefined} />
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
    </div>
  )
}
