import Link from 'next/link'

import { NoPermission } from '@/components/common/NoPermission'
import { InvoiceFilters } from '@/components/purchases/InvoiceFilters'
import { InvoiceTable } from '@/components/purchases/InvoiceTable'
import { ErrorState } from '@/components/ui/state'
import { readFromApi } from '@/lib/api/server'
import { count } from '@/lib/format'
import type { InvoiceList, SupplierList } from '@/lib/purchases/types'

export const metadata = {
  title: 'Facturas — Plataforma Cordillera',
}

interface PageProps {
  searchParams: Promise<{
    q?: string
    supplier_id?: string
    issued_from?: string
    issued_to?: string
    order?: string
    payment_state?: string
    with_receipt?: string
    review_state?: string
  }>
}

/**
 * Los cortes de la guía (`3f`), y qué filtro es cada uno.
 *
 * Son enlaces con el filtro puesto y no una pestaña que guarda estado: lo que
 * se está mirando viaja en la URL, así que se comparte por chat con quien tiene
 * que mirarlo y llega filtrado.
 *
 * **«Vencidas» no está**, y el diseño la dibuja. Sería *vencida y sin saldar*,
 * y la API filtra por vencimiento o por estado de pago pero no por los dos a la
 * vez: la pestaña traería también las vencidas ya pagadas, que es justamente el
 * conjunto que a nadie le urge. Lo que vence sin recibo tiene su propia pantalla
 * —el calendario— y ahí sí está contestado.
 */
const VIEWS = [
  { id: 'todas', label: 'Todas', query: {} },
  { id: 'revisar', label: 'Por revisar', query: { review_state: 'PENDING' } },
  { id: 'sin-recibo', label: 'Sin recibo', query: { with_receipt: 'false' } },
  { id: 'parciales', label: 'Parciales', query: { payment_state: 'PARCIAL' } },
  { id: 'saldadas', label: 'Saldadas', query: { payment_state: 'SALDADA' } },
] as const

/** Qué corte está abierto, leído de los filtros que trae la URL. */
function currentView(filters: Record<string, string | undefined>): string {
  if (filters.review_state === 'PENDING') return 'revisar'
  if (filters.with_receipt === 'false') return 'sin-recibo'
  if (filters.payment_state === 'PARCIAL') return 'parciales'
  if (filters.payment_state === 'SALDADA') return 'saldadas'
  return 'todas'
}

function hrefFor(query: Record<string, string>): string {
  const params = new URLSearchParams(query)
  const text = params.toString()
  return text ? `/facturas?${text}` : '/facturas'
}

/**
 * Las facturas de compra (H8 de 004, H1 de 005), con la forma de la guía (`3f`).
 *
 * Encabezado con el estado de la carpeta, la fila de cortes con la cuenta
 * encendida sobre el que espera trabajo, los filtros finos y la tabla.
 *
 * **Las tres puertas de ingreso del diseño no están, y no es un olvido.** La
 * guía dibuja arriba tres tarjetas: arrastrar archivos, una casilla de mail y la
 * descarga automática del portal. De las tres, la única que existe es la
 * tercera: no hay carga de archivos ni casilla de correo en el backend, y
 * dibujar una zona de arrastre que no recibe nada sería una promesa. Lo que sí
 * está —la reconstrucción a mano de una fila que el portal publicó rota— vive
 * en la cola de pendientes, que es donde se ve el problema.
 *
 * Los filtros van en la URL y no en el estado del componente a propósito: una
 * pantalla filtrada se comparte por chat con quien tiene que mirarla, y así
 * llega filtrada.
 *
 * Lo que la búsqueda alcanza lo decide el backend y no esta pantalla: el número,
 * el nombre tal como llegó escrito y —para una factura ya asignada— el CUIT y la
 * razón social del padrón (RF-41, RF-42). Acá sólo se arma la URL.
 */
export default async function InvoicesPage({ searchParams }: PageProps) {
  const filters = await searchParams
  const query = new URLSearchParams({ limit: '200' })
  for (const name of [
    'q',
    'supplier_id',
    'issued_from',
    'issued_to',
    'order',
    'payment_state',
    'review_state',
    'with_receipt',
  ] as const) {
    const value = filters[name]
    if (value) query.set(name, value)
  }

  // Los dos últimos pedidos existen sólo por su `total`: cuántas facturas
  // esperan una decisión y cuántas están sin recibo son preguntas sobre el
  // sistema, no sobre la página que se está mirando (RF-32). Contando `items`
  // decían «46 sin recibo» cuando el límite de 200 recortaba la lista, y encima
  // cambiaban al filtrar por otra cosa.
  const [read, suppliers, missing, toReview] = await Promise.all([
    readFromApi<InvoiceList>(`/invoices?${query.toString()}`),
    readFromApi<SupplierList>('/suppliers'),
    readFromApi<InvoiceList>('/invoices?with_receipt=false&limit=1'),
    readFromApi<InvoiceList>('/invoices?review_state=PENDING&limit=1'),
  ])

  // Un 403 y una caída del backend son dos frases distintas. Decirle «no tenés
  // permiso» al dueño porque la API no contestó lo manda a pedirse a sí mismo
  // un permiso que ya tiene, y a no mirar el problema que sí hay.
  if (!read.ok) {
    if (read.failure === 'unauthorized') {
      return <NoPermission what="las facturas de compra" />
    }
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Facturas</h1>
        <ErrorState title="No pudimos traer las facturas.">
          Probá de nuevo en unos minutos.
        </ErrorState>
      </div>
    )
  }

  const listing = read.data
  const withoutReceipt = missing.ok ? missing.data.total : null
  const pending = toReview.ok ? toReview.data.total : 0
  const view = currentView(filters)

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-4 rounded-xl border border-border bg-card px-6 py-5">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Facturas</h1>
          <p className="text-sm text-muted-foreground">
            {count(listing.total)} registradas
            {pending > 0 && ` · ${count(pending)} esperando una decisión tuya`}
            {withoutReceipt !== null && ` · ${count(withoutReceipt)} sin recibo`}.
          </p>
        </div>

        {/*
          Las otras tres pantallas de la carpeta. Van acá, en contorno, y no
          entre los cortes de abajo: un corte cambia lo que muestra esta tabla,
          y esto lleva a otra pantalla. Mezclarlos hacía que la fila de nueve
          enlaces no dijera cuáles eran de ida y cuáles de filtro.
        */}
        <div className="flex flex-wrap items-center gap-2">
          {[
            { href: '/facturas/revision', label: 'Revisar apartadas' },
            { href: '/facturas/pagos', label: 'Comprobantes por repartir' },
            { href: '/facturas/incidentes', label: 'Incidentes de recibo' },
          ].map(door => (
            <Link
              key={door.href}
              className="inline-flex h-10 items-center rounded-md border border-input bg-card px-4 text-sm font-semibold text-foreground hover:bg-muted"
              href={door.href}
            >
              {door.label}
            </Link>
          ))}
        </div>
      </header>

      <div className="overflow-hidden rounded-xl border border-border bg-card">
        {/*
          La fila de cortes de la guía. El que espera trabajo lleva su cuenta
          encendida, y en cero no se pinta: un ámbar con un cero al lado enseña
          que el color no quiere decir nada.
        */}
        <nav
          aria-label="Cortes de la lista"
          className="flex gap-1 overflow-x-auto border-b border-border px-2"
        >
          {VIEWS.map(option => {
            const current = option.id === view
            const badge = option.id === 'revisar' && pending > 0
            return (
              <Link
                key={option.id}
                href={hrefFor(option.query)}
                aria-current={current ? 'page' : undefined}
                className={`-mb-px flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-2.5 text-sm transition-colors ${
                  current
                    ? 'border-foreground font-semibold text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                {option.label}
                {badge && (
                  <span className="amount rounded-full bg-warn-surface px-1.5 py-0.5 text-[10px] font-semibold text-warn">
                    {count(pending)}
                  </span>
                )}
              </Link>
            )
          })}
        </nav>

        <div className="border-b border-border px-4 py-3">
          <InvoiceFilters suppliers={suppliers.ok ? suppliers.data.items : []} values={filters} />
        </div>

        <div className="px-4 py-2">
          <InvoiceTable invoices={listing.items} />
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        Si el número, el proveedor y el monto ya existen, la factura no entra dos veces: queda como
        posible duplicada hasta que alguien decida.
      </p>
    </div>
  )
}
