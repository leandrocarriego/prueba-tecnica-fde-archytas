import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { PeriodPicker } from '@/components/sales/PeriodPicker'
import { SalesTable } from '@/components/sales/SalesTable'
import { Button } from '@/components/ui/button'
import { Notice } from '@/components/ui/notice'
import { ErrorState } from '@/components/ui/state'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import { count } from '@/lib/format'
import type { ReviewQueue, SaleList } from '@/lib/sales/types'

export const metadata = {
  title: 'Ventas — Plataforma Cordillera',
}

/** Cuántas filas trae una página del listado. */
const PAGE_SIZE = 100

interface SalesSearchParams {
  desde?: string
  hasta?: string
  pagina?: string
  estado?: string
}

/**
 * Los dos cortes del listado, y por qué son dos y no tres.
 *
 * Lo **apartado** no está acá: espera una decisión, y lo que espera una decisión
 * vive en «Para decidir» y en ningún otro lado. Lo que sí está es lo que ya no
 * espera nada — lo que el sistema unificó solo por idéntico, y la versión que
 * alguien descartó al elegir otra— porque forma parte de lo que cada indicador
 * dejó afuera, y `RF-26` pide que eso se pueda ver.
 */
const VIEWS = {
  suman: { state: 'COUNTED', label: 'Que suman' },
  'no-suman': { state: 'DISCARDED', label: 'Que no suman' },
} as const

type View = keyof typeof VIEWS

function viewFrom(value: string | undefined): View {
  return value === 'no-suman' ? 'no-suman' : 'suman'
}

/** Un número de página de la barra de direcciones, o la primera. */
function pageFrom(value: string | undefined): number {
  const parsed = Number.parseInt(value ?? '', 10)
  return Number.isInteger(parsed) && parsed > 1 ? parsed : 1
}

/**
 * El listado de ventas: lo que la plataforma **puede sumar**, y nada más.
 *
 * Era la cola de revisión —repetidas, rotas, resueltas y descartadas, las cuatro
 * en la misma pantalla— y no era un listado de ventas: era la bandeja de
 * pendientes de ventas viviendo aparte de la bandeja de pendientes de todo lo
 * demás. Ahora lo que espera una decisión está en «Para decidir», que es la
 * única cola de la plataforma (RF-06 de 011), y acá queda la lista.
 *
 * **Sólo lo que suma** (`state=COUNTED`). Es la decisión que tomó el dueño y
 * tiene una consecuencia que conviene decir en voz alta: una venta apartada no
 * aparece acá ni marcada, así que este listado y los indicadores del tablero
 * cuentan lo mismo. Lo que quedó afuera no se esconde —el aviso de arriba dice
 * cuántas son y lleva a la cola— pero no se mezcla con lo que ya es firme.
 *
 * La forma es la de la lista de precios (guía visual `3k`), y a propósito: es la
 * misma clase de pantalla, y dos padrones del mismo producto dibujados distinto
 * se leen como dos productos.
 */
export default async function SalesPage({
  searchParams,
}: {
  searchParams: Promise<SalesSearchParams>
}) {
  const { desde, hasta, pagina, estado } = await searchParams
  const page = pageFrom(pagina)
  const view = viewFrom(estado)
  const session = await getSession()

  const query = new URLSearchParams({
    state: VIEWS[view].state,
    limit: String(PAGE_SIZE),
    skip: String((page - 1) * PAGE_SIZE),
  })
  if (desde) query.set('since', desde)
  if (hasta) query.set('until', hasta)

  const [sales, queue] = await Promise.all([
    fetchFromApi<SaleList>(`/sales?${query.toString()}`),
    /*
      Cuántas esperan una decisión, para poder decirlo acá y llevar a la cola.
      Sólo se pregunta si quien mira puede resolverlas: la cola de ventas está
      detrás de `SALES` en escritura, y pedirla igual sería un 403 que
      `?? null` disfrazaría de «no hay ninguna» — un cero que nadie escribió.
    */
    session !== null && canEdit(session.permissions, 'SALES')
      ? fetchFromApi<ReviewQueue>('/sales/review')
      : Promise.resolve(null),
  ])

  if (sales === null) {
    return <NoPermission what="las ventas" />
  }

  const held = queue?.held ?? 0
  const shown = sales.items.length
  const first = shown === 0 ? 0 : (page - 1) * PAGE_SIZE + 1
  const last = (page - 1) * PAGE_SIZE + shown

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-4 rounded-xl border border-border bg-card px-6 py-5">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Ventas</h1>
          <p className="text-sm text-muted-foreground">
            {count(sales.total)} {sales.total === 1 ? 'venta' : 'ventas'}{' '}
            {view === 'suman' ? 'que suman' : 'que no suman'}
            {desde || hasta ? ' en el período elegido' : ''}.
          </p>
        </div>

        <PeriodPicker
          label="Período de las ventas"
          fromName="desde"
          toName="hasta"
          from={desde}
          to={hasta}
          /*
            El corte viaja; la página no. Cambiar el período no tiene por qué
            devolverte a «Que suman» si estabas mirando lo otro, y en cambio la
            página cuatro de un período puede no existir en el siguiente: una
            lista vacía sin explicación se lee como «no hay ventas».
          */
          keep={{ estado: view === 'suman' ? undefined : view }}
        />
      </header>

      {/*
        Lo que quedó afuera se dice, con la puerta al lado (Artículo II). No se
        muestra acá: se cuenta, y el que decide entra a la cola donde está todo
        lo demás que espera una decisión.
      */}
      {held > 0 && (
        <Notice
          tone="warn"
          title={
            held === 1
              ? 'Hay 1 venta esperando una decisión'
              : `Hay ${held} ventas esperando una decisión`
          }
          action={
            <Button asChild variant="outline">
              <Link href="/revision?area=SALES">Ir a decidir</Link>
            </Button>
          }
        >
          Están repetidas o les falta un dato, así que no suman en ningún indicador hasta que
          alguien resuelva.
        </Notice>
      )}

      {sales.items.length === 0 && page > 1 ? (
        <ErrorState title="Esa página no tiene ventas.">
          Volvé a la primera para ver el listado.
        </ErrorState>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-card">
          {/*
            Los dos cortes, como enlaces: viajan en la URL igual que el período
            y la página, así que se comparten y el navegador los recuerda. No es
            un naranja — mirar otro corte es navegación, no la decisión de la
            pantalla, y acá no hay ninguna decisión que tomar (`UI-05`).
          */}
          <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-3">
            {(Object.keys(VIEWS) as View[]).map(id => (
              <Link
                key={id}
                href={linkTo({ estado: id === 'suman' ? undefined : id, desde, hasta })}
                aria-current={id === view ? 'page' : undefined}
                className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                  id === view
                    ? 'border-input bg-muted text-foreground'
                    : 'border-input bg-card text-muted-foreground hover:bg-muted'
                }`}
              >
                {VIEWS[id].label}
              </Link>
            ))}
            {view === 'no-suman' && (
              <p className="text-xs text-muted-foreground">
                No esperan una decisión: el sistema las unificó por idénticas, o alguien eligió otra
                versión.
              </p>
            )}
          </div>

          <SalesTable items={sales.items} showReason={view === 'no-suman'} />

          {/*
            El pie del listado dice qué tramo se está mirando. Es un número que
            se puede verificar mirando la tabla, que es la única clase de número
            que esta pantalla escribe.
          */}
          {sales.total > PAGE_SIZE && (
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3">
              <p className="text-sm text-muted-foreground">
                Mostrando {count(first)}–{count(last)} de {count(sales.total)}.
              </p>
              <div className="flex items-center gap-2">
                <Pager to={page - 1} desde={desde} hasta={hasta} view={view} disabled={page === 1}>
                  Anterior
                </Pager>
                <Pager
                  to={page + 1}
                  desde={desde}
                  hasta={hasta}
                  view={view}
                  disabled={last >= sales.total}
                >
                  Siguiente
                </Pager>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Un paso del listado, como enlace y no como botón.
 *
 * La página viaja en la URL —igual que el período— así que se puede compartir y
 * el navegador la recuerda al volver. Un botón que empuja estado no hace ninguna
 * de las dos cosas.
 */
function Pager({
  to,
  desde,
  hasta,
  view,
  disabled,
  children,
}: {
  to: number
  desde?: string
  hasta?: string
  view: View
  disabled: boolean
  children: React.ReactNode
}) {
  if (disabled) {
    return (
      <span className="rounded-md border border-border px-3 py-1.5 text-sm text-muted-ink">
        {children}
      </span>
    )
  }

  return (
    <Link
      className="rounded-md border border-input bg-card px-3 py-1.5 text-sm font-semibold text-foreground hover:bg-muted"
      href={linkTo({
        desde,
        hasta,
        estado: view === 'suman' ? undefined : view,
        pagina: to > 1 ? String(to) : undefined,
      })}
    >
      {children}
    </Link>
  )
}

/**
 * Una dirección de esta pantalla, con lo que se le pase y nada más.
 *
 * Escrito una vez porque los tres controles —el corte, el período y la página—
 * comparten la barra de direcciones, y cada uno tiene que conservar lo que
 * eligieron los otros dos. Lo que se omite se cae de la URL: la primera página
 * y el corte por defecto no se escriben, así que `/ventas` a secas es siempre la
 * pantalla inicial.
 */
function linkTo(values: Record<string, string | undefined>): string {
  const params = new URLSearchParams()
  for (const [name, value] of Object.entries(values)) {
    if (value) params.set(name, value)
  }
  const query = params.toString()
  return query ? `/ventas?${query}` : '/ventas'
}
