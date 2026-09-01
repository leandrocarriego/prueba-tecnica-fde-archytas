import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { Tile } from '@/components/common/Tile'
import { NoPermission } from '@/components/common/NoPermission'
import { OrderTable } from '@/components/purchases/OrderTable'
import { Button } from '@/components/ui/button'
import { selectClassName } from '@/components/ui/input'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import { count } from '@/lib/format'
import type { PurchaseOrderList, SupplierList } from '@/lib/purchases/types'

export const metadata = {
  title: 'Órdenes de compra — Plataforma Cordillera',
}

interface PageProps {
  searchParams: Promise<{
    estado?: string
    estancadas?: string
    apartadas?: string
    proveedor?: string
  }>
}

/** Una dirección de esta pantalla, conservando sólo lo que se le pase. */
function hrefFor(values: Record<string, string | undefined>): string {
  const params = new URLSearchParams()
  for (const [name, value] of Object.entries(values)) {
    if (value) params.set(name, value)
  }
  const query = params.toString()
  return query ? `/ordenes?${query}` : '/ordenes'
}

/**
 * Las órdenes de compra y en qué punto del recorrido está cada una (H1 y H2 de
 * 007), con la forma de la guía visual (`3i`).
 *
 * Encabezado con el estado de la carpeta, los cortes como píldoras, las cuatro
 * cuentas —**lo que se pidió y nadie siguió va arriba, no enterrado en la
 * lista**, que es lo que la guía pide— y la tabla.
 *
 * **Dos piezas del diseño no están, y las dos son por la misma razón: el dato no
 * existe de este lado.**
 *
 * La primera es la línea de tiempo *pedido → recibido → facturado → pagado*. El
 * portal publica el estado como **un texto libre y una fecha**, no como cuatro
 * hitos con su momento, así que dibujar los cuatro puntos exigiría inventar tres
 * de ellos. Lo que sí se puede decir es dónde está la orden ahora y desde
 * cuándo, y eso es lo que dice cada fila.
 *
 * La segunda es la tabla de ítems con lo pedido contra lo recibido. Acá una
 * orden **es** una línea —un producto, una cantidad, un importe—, no una
 * cabecera con cinco ítems, y no hay cantidad recibida en ninguna parte.
 *
 * Tampoco hay «Nueva orden», por lo mismo que no hay «Nuevo proveedor»: las
 * órdenes salen del portal y la plataforma no crea ninguna (Artículo I).
 *
 * Lo que sí está, y es la otra mitad de la guía, es el aviso de **pedido
 * repetido**: si hay otra orden abierta del mismo producto al mismo proveedor,
 * la fila lo dice y se puede descartar la sospecha.
 */
export default async function OrdersPage({ searchParams }: PageProps) {
  const filters = await searchParams
  const query = new URLSearchParams({ limit: '200' })
  if (filters.estado) query.set('status_text', filters.estado)
  if (filters.estancadas) query.set('only_stalled', 'true')
  if (filters.apartadas) query.set('only_in_review', 'true')
  // RF-06: filtrar por estado **y por proveedor**. La mitad del proveedor
  // vivía sólo en la API y no había control que la pidiera.
  if (filters.proveedor) query.set('supplier_id', filters.proveedor)

  const [listing, suppliers, session] = await Promise.all([
    fetchFromApi<PurchaseOrderList>(`/purchase-orders?${query.toString()}`),
    // El padrón, para resolver una orden apartada desde la misma lista (H8).
    fetchFromApi<SupplierList>('/suppliers'),
    getSession(),
  ])

  if (listing === null) {
    return <NoPermission what="las órdenes de compra" />
  }

  // Sospechas de pedido repetido que nadie descartó todavía. Se cuenta sobre lo
  // que trajo la página y no sobre el total, y por eso el subtítulo dice «en
  // esta vista»: es un número que se puede verificar mirando la tabla.
  const repeats = listing.items.filter(
    order => order.repeat_of_order_id !== null && order.repeat_dismissed_at === null
  ).length

  const views = [
    { id: 'todas', label: 'Todas', href: hrefFor({ proveedor: filters.proveedor }) },
    ...Object.entries(listing.per_status).map(([status, howMany]) => ({
      id: `estado:${status}`,
      label: `${status} (${howMany})`,
      href: hrefFor({ estado: status, proveedor: filters.proveedor }),
    })),
    {
      id: 'estancadas',
      label: `Atrasadas (${listing.stalled})`,
      href: hrefFor({ estancadas: '1', proveedor: filters.proveedor }),
    },
    {
      id: 'apartadas',
      label: `Apartadas (${listing.held})`,
      href: hrefFor({ apartadas: '1', proveedor: filters.proveedor }),
    },
  ]
  const current = filters.estancadas
    ? 'estancadas'
    : filters.apartadas
      ? 'apartadas'
      : filters.estado
        ? `estado:${filters.estado}`
        : 'todas'

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-4 rounded-xl border border-border bg-card px-6 py-5">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Órdenes de compra
          </h1>
          <p className="text-sm text-muted-foreground">
            {count(listing.total)} en esta vista
            {listing.stalled > 0 && ` · ${count(listing.stalled)} sin novedades hace días`}
            {listing.held > 0 && ` · ${count(listing.held)} sin proveedor asignado`}.
          </p>
        </div>

        {/*
          El filtro por proveedor: un `form` con GET y nada de JavaScript, y los
          demás filtros en campos ocultos para que elegir un proveedor no borre
          en silencio el corte que ya estaba puesto.
        */}
        <form action="/ordenes" className="flex flex-wrap items-end gap-2" method="get">
          {filters.estado && <input name="estado" type="hidden" value={filters.estado} />}
          {filters.estancadas && (
            <input name="estancadas" type="hidden" value={filters.estancadas} />
          )}
          {filters.apartadas && <input name="apartadas" type="hidden" value={filters.apartadas} />}
          <label className="flex flex-col gap-1.5">
            <span className="section-label">Proveedor</span>
            <select
              className={selectClassName}
              defaultValue={filters.proveedor ?? ''}
              id="proveedor"
              name="proveedor"
            >
              <option value="">Todos</option>
              {(suppliers?.items ?? []).map(supplier => (
                <option key={supplier.id} value={String(supplier.id)}>
                  {supplier.legal_name}
                </option>
              ))}
            </select>
          </label>
          {/* Filtrar no es la tarea de la pantalla —leer las órdenes lo es—. */}
          <Button type="submit" variant="outline" className="h-9">
            Filtrar
          </Button>
        </form>
      </header>

      <div className="flex flex-wrap gap-4">
        <Tile
          label="En esta vista"
          value={count(listing.total)}
          sub="Órdenes que coinciden con el corte elegido."
        />
        {/*
          «Lo que se pidió y nadie siguió aparece arriba, no enterrado en una
          lista» — la frase de la guía, y la razón por la que estas dos van
          acentuadas cuando no están en cero.
        */}
        <Tile
          label="Atrasadas"
          value={count(listing.stalled)}
          accent={listing.stalled > 0}
          sub="Sin novedades desde hace más días que los que fijó el dueño."
        />
        <Tile
          label="Sin proveedor"
          value={count(listing.held)}
          accent={listing.held > 0}
          sub={
            listing.held === 0
              ? 'Todas atribuidas a un proveedor del padrón.'
              : 'Esperan que alguien diga de quién son.'
          }
        />
        <Tile
          label="Posible pedido repetido"
          value={count(repeats)}
          sub={
            repeats === 0
              ? 'Ninguna sospecha sin descartar.'
              : 'Mismo producto y proveedor que otra orden abierta.'
          }
        />
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <nav
          aria-label="Cortes de las órdenes"
          className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-3"
        >
          {views.map(view => (
            <Link
              key={view.id}
              href={view.href}
              aria-current={view.id === current ? 'page' : undefined}
              className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                view.id === current
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-input bg-card text-muted-foreground hover:bg-muted'
              }`}
            >
              {view.label}
            </Link>
          ))}
        </nav>

        <div className="px-4 py-2">
          <OrderTable
            orders={listing.items}
            suppliers={suppliers?.items ?? []}
            canEdit={canEdit(session?.permissions ?? {}, 'PURCHASE_ORDERS')}
          />
        </div>
      </div>
    </div>
  )
}
