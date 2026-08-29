import Link from 'next/link'

import { formatMoment, formatPrice, formatVariation, variationTone } from '@/lib/catalog/format'
import type { Price } from '@/lib/catalog/types'

interface PriceTableProps {
  items: Price[]
}

/**
 * The price list in force (RF-04).
 *
 * A Server Component: it renders data and has no interactivity of its own, so
 * there is no reason to ship it to the browser.
 *
 * Two marks earn their place in the table. A **rise above the threshold** is
 * what the owner asked to see without reading a hundred rows (RF-25), and a
 * product that **did not come in the last list** says so next to the price it
 * is still showing, instead of looking as fresh as the rest (RF-08).
 */
export function PriceTable({ items }: PriceTableProps) {
  if (items.length === 0) {
    return (
      <p className="rounded border border-dashed p-8 text-center text-muted-foreground">
        Todavía no hay precios cargados. Se cargan solos con la próxima consulta al portal.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-left">
          <tr>
            <th className="p-3 font-medium">Código</th>
            <th className="p-3 font-medium">Descripción</th>
            <th className="p-3 text-right font-medium">Precio</th>
            <th className="p-3 text-right font-medium">Anterior</th>
            <th className="p-3 text-right font-medium">Vs. mes pasado</th>
            <th className="p-3 font-medium">Actualizado</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr
              key={item.product_id}
              className={`border-t ${item.is_highlighted ? 'bg-amber-50' : ''}`}
            >
              <td className="p-3 font-mono">
                <Link className="underline underline-offset-2" href={`/precios/${item.product_id}`}>
                  {item.code}
                </Link>
              </td>
              <td className="p-3">
                {item.description}
                {item.is_highlighted && (
                  <span className="ml-2 rounded bg-amber-200 px-2 py-0.5 text-xs text-amber-900">
                    Subió fuerte
                  </span>
                )}
                {item.is_stale && (
                  <span className="ml-2 rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-700">
                    No vino en la última lista
                  </span>
                )}
              </td>
              <td className="p-3 text-right font-medium">{formatPrice(item.price)}</td>
              <td className="p-3 text-right text-muted-foreground">
                {formatPrice(item.previous_price)}
              </td>
              <td className={`p-3 text-right ${variationTone(item.monthly_variation_pct)}`}>
                {formatVariation(item.monthly_variation_pct)}
              </td>
              <td className="p-3 text-muted-foreground">{formatMoment(item.effective_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
