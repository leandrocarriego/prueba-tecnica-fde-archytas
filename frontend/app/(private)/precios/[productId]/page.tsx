import Link from 'next/link'
import { notFound } from 'next/navigation'

import { formatDay, formatPrice, formatVariation, variationTone } from '@/lib/catalog/format'
import { fetchFromApi } from '@/lib/api/server'
import type { PriceHistory } from '@/lib/catalog/types'

/** Where a point came from, in words. */
const SOURCE_LABEL: Record<string, string> = {
  PORTAL: 'Publicado por el portal',
  SYSTEM: 'Registrado por el sistema',
}

/**
 * How the price of one product moved (RF-23), and against last month (RF-24).
 *
 * The history has two origins and the page says which is which: the points the
 * portal already published when the product was first seen (RF-38), and the
 * changes the platform has seen since.
 */
export default async function ProductPage({ params }: { params: Promise<{ productId: string }> }) {
  const { productId } = await params
  const history = await fetchFromApi<PriceHistory>(`/prices/${productId}/history`)

  if (history === null) notFound()

  const points = [...history.points].reverse()

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-8">
      <Link className="text-sm text-muted-foreground underline" href="/precios">
        « Volver a la lista de precios
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">{history.description}</h1>
        <p className="font-mono text-muted-foreground">{history.code}</p>
      </header>

      <section className="flex flex-wrap gap-8 rounded border p-4">
        <div>
          <p className="text-sm text-muted-foreground">Precio vigente</p>
          <p className="text-2xl font-bold">{formatPrice(history.price)}</p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Contra el mes pasado</p>
          <p className={`text-2xl font-bold ${variationTone(history.monthly_variation_pct)}`}>
            {formatVariation(history.monthly_variation_pct)}
          </p>
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Evolución del precio</h2>
        {points.length === 0 ? (
          <p className="rounded border border-dashed p-6 text-center text-muted-foreground">
            Todavía no hay historial para este producto.
          </p>
        ) : (
          <div className="overflow-x-auto rounded border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left">
                <tr>
                  <th className="p-3 font-medium">Fecha</th>
                  <th className="p-3 text-right font-medium">Precio</th>
                  <th className="p-3 font-medium">Origen</th>
                </tr>
              </thead>
              <tbody>
                {points.map(point => (
                  <tr key={`${point.changed_at}-${point.price}`} className="border-t">
                    <td className="p-3">{formatDay(point.changed_at)}</td>
                    <td className="p-3 text-right font-medium">{formatPrice(point.price)}</td>
                    <td className="p-3 text-muted-foreground">
                      {SOURCE_LABEL[point.source] ?? point.source}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  )
}
