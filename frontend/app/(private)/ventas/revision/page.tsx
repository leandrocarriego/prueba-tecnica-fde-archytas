import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { SalesReview } from '@/components/sales/SalesReview'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { ReviewQueue, SaleList } from '@/lib/sales/types'

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
  // Lo descartado se pide aparte y a propósito: **no está en la cola**, porque
  // no espera ninguna decisión. Pero es la mitad de lo que los indicadores
  // excluyen, y RF-26 pide poder ver los registros que un número dejó afuera —
  // hasta acá, la mitad unificada no se veía desde ningún lado.
  const [queue, discarded, session] = await Promise.all([
    fetchFromApi<ReviewQueue>('/sales/review'),
    fetchFromApi<SaleList>('/sales?state=DISCARDED&limit=200'),
    getSession(),
  ])

  if (queue === null) {
    return <NoPermission what="las ventas" />
  }

  return (
    <div className="space-y-8">
      <Link className="text-sm text-link hover:underline" href="/tablero">
        « Volver al tablero
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Ventas apartadas</h1>
        <p className="text-sm text-muted-foreground">
          {queue.held} registros apartados en total. Ninguno entra en los indicadores hasta que
          alguien decida.
        </p>
      </header>

      <SalesReview
        queue={queue}
        discarded={discarded?.items ?? []}
        canEdit={canEdit(session?.permissions ?? {}, 'SALES')}
      />
    </div>
  )
}
