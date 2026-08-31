import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { ReviewQueue } from '@/components/purchases/ReviewQueue'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { InvoiceList, SupplierList } from '@/lib/purchases/types'

export const metadata = {
  title: 'Facturas en revisión — Plataforma Cordillera',
}

/**
 * Las facturas que el sistema no pudo resolver solo (H5 de 004).
 *
 * Es la mitad visible del Artículo II para las compras: nada se descarta, así
 * que todo lo que no se pudo decidir sin una persona termina acá con el motivo,
 * y lo que se decide se guarda para no volver a preguntarlo.
 */
export default async function InvoiceReviewPage() {
  const [queue, suppliers, session] = await Promise.all([
    fetchFromApi<InvoiceList>('/invoice-review?limit=200'),
    fetchFromApi<SupplierList>('/suppliers'),
    getSession(),
  ])

  if (queue === null) {
    return <NoPermission what="la revisión de facturas" />
  }

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <Link className="text-sm text-muted-foreground underline" href="/facturas">
        « Volver a las facturas
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Facturas en revisión</h1>
        <p className="text-sm text-muted-foreground">
          {queue.total === 0
            ? 'No quedó nada esperando una decisión.'
            : `${queue.total} ${queue.total === 1 ? 'factura espera' : 'facturas esperan'} una decisión. Ninguna suma en los totales mientras tanto.`}
        </p>
      </header>

      <ReviewQueue
        invoices={queue.items}
        suppliers={suppliers?.items ?? []}
        canDecide={canEdit(session?.permissions ?? {}, 'PURCHASE_INVOICES')}
      />
    </main>
  )
}
