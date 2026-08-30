import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { OrderTable } from '@/components/purchases/OrderTable'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { PurchaseOrderList } from '@/lib/purchases/types'

export const metadata = {
  title: 'Órdenes de compra — Plataforma Cordillera',
}

interface PageProps {
  searchParams: Promise<{ estado?: string; estancadas?: string }>
}

/**
 * Las órdenes de compra y en qué punto del recorrido está cada una (H1 y H2 de 007).
 */
export default async function OrdersPage({ searchParams }: PageProps) {
  const filters = await searchParams
  const query = new URLSearchParams({ limit: '200' })
  if (filters.estado) query.set('status_text', filters.estado)
  if (filters.estancadas) query.set('only_stalled', 'true')

  const [listing, session] = await Promise.all([
    fetchFromApi<PurchaseOrderList>(`/purchase-orders?${query.toString()}`),
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
          {listing.total} órdenes en esta vista · {listing.stalled} estancadas.
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
      </nav>

      <OrderTable
        orders={listing.items}
        canEdit={canEdit(session?.permissions ?? {}, 'PURCHASE_ORDERS')}
      />
    </main>
  )
}
