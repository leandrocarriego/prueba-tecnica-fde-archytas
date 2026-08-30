import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { SalesReview } from '@/components/sales/SalesReview'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { ReviewQueue } from '@/lib/sales/types'

export const metadata = {
  title: 'Ventas apartadas — Plataforma Cordillera',
}

/**
 * Las ventas que ningún indicador puede sumar todavía (H2, H3 y H5 de 009).
 *
 * Es la frase del cliente hecha pantalla: *"que se nos avise cuáles son, no que
 * se sumen como si fueran válidas"*.
 */
export default async function SalesReviewPage() {
  const [queue, session] = await Promise.all([
    fetchFromApi<ReviewQueue>('/sales/review'),
    getSession(),
  ])

  if (queue === null) {
    return <NoPermission what="las ventas" />
  }

  return (
    <main className="mx-auto max-w-5xl space-y-8 p-8">
      <Link className="text-sm text-muted-foreground underline" href="/tablero">
        « Volver al tablero
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Ventas apartadas</h1>
        <p className="text-sm text-muted-foreground">
          {queue.held} registros apartados en total. Ninguno entra en los indicadores hasta que
          alguien decida.
        </p>
      </header>

      <SalesReview queue={queue} canEdit={canEdit(session?.permissions ?? {}, 'SALES')} />
    </main>
  )
}
