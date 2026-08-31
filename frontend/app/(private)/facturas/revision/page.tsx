import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { ReviewQueue } from '@/components/purchases/ReviewQueue'
import { readFromApi } from '@/lib/api/server'
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
  const [read, suppliers, session] = await Promise.all([
    readFromApi<InvoiceList>('/invoice-review?limit=200'),
    readFromApi<SupplierList>('/suppliers'),
    getSession(),
  ])

  // La cola vacía y la cola que no se pudo traer se ven igual si no se
  // distinguen, y dicen lo contrario: «no quedó nada esperando» sobre una API
  // caída es la frase que hace que nadie vuelva a mirar.
  if (!read.ok) {
    if (read.failure === 'unauthorized') {
      return <NoPermission what="la revisión de facturas" />
    }
    return (
      <main className="mx-auto max-w-4xl space-y-6 p-8">
        <h1 className="text-2xl font-bold">Facturas en revisión</h1>
        <p className="rounded border border-danger-border bg-danger-surface p-4 text-sm text-danger">
          No pudimos traer la cola de revisión. Probá de nuevo en unos minutos.
        </p>
      </main>
    )
  }

  const queue = read.data

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
        suppliers={suppliers.ok ? suppliers.data.items : []}
        canDecide={canEdit(session?.permissions ?? {}, 'PURCHASE_INVOICES')}
      />
    </main>
  )
}
