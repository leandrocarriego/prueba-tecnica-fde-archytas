import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { OrderTable } from '@/components/purchases/OrderTable'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
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

/**
 * Las órdenes de compra y en qué punto del recorrido está cada una (H1 y H2 de 007).
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

  return (
    <main className="mx-auto max-w-6xl space-y-8 p-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Órdenes de compra</h1>
        <p className="text-sm text-muted-foreground">
          {listing.total} órdenes en esta vista · {listing.stalled} estancadas · {listing.held}{' '}
          apartadas para revisión.
        </p>
      </header>

      <nav className="flex flex-wrap gap-4 text-sm">
        <Link className="underline" href="/ordenes">
          Todas
        </Link>
        {Object.entries(listing.per_status).map(([status, howMany]) => (
          <Link
            key={status}
            className="underline"
            href={`/ordenes?estado=${encodeURIComponent(status)}`}
          >
            {status} ({howMany})
          </Link>
        ))}
        <Link className="underline" href="/ordenes?estancadas=1">
          Sólo estancadas ({listing.stalled})
        </Link>
        <Link className="underline" href="/ordenes?apartadas=1">
          Sólo apartadas ({listing.held})
        </Link>
      </nav>

      {/*
        Un form con GET y sin JavaScript: el filtro es un enlace con otra
        query, igual que los de arriba, y la pantalla sigue siendo un Server
        Component. Los demás filtros viajan en campos ocultos para que elegir
        un proveedor no borre en silencio el estado que ya estaba puesto.
      */}
      <form action="/ordenes" className="flex flex-wrap items-center gap-2 text-sm" method="get">
        {filters.estado && <input name="estado" type="hidden" value={filters.estado} />}
        {filters.estancadas && <input name="estancadas" type="hidden" value={filters.estancadas} />}
        {filters.apartadas && <input name="apartadas" type="hidden" value={filters.apartadas} />}
        <label htmlFor="proveedor">Proveedor</label>
        <select
          className="rounded border p-2"
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
        <button className="rounded border px-3 py-2" type="submit">
          Filtrar
        </button>
      </form>

      <OrderTable
        orders={listing.items}
        suppliers={suppliers?.items ?? []}
        canEdit={canEdit(session?.permissions ?? {}, 'PURCHASE_ORDERS')}
      />
    </main>
  )
}
