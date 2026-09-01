import Link from 'next/link'

import { formatVariation } from '@/lib/catalog/format'
import type { PriceSummary } from '@/lib/catalog/types'

interface PriceSummaryCardsProps {
  summary: PriceSummary
}

/**
 * Las cuatro cuentas arriba de la lista de precios (guía visual `3k`).
 *
 * Cada una es un agregado de **todo el catálogo**, no de la página que la tabla
 * muestra: salen de `/prices/summary`, que las calcula sobre un dato que el
 * catálogo ya tiene —el precio en vigencia contra el anterior, si el producto
 * vino en la última lista, si tiene rubro—. Ningún número está estimado.
 *
 * «Nuevos sin rubro» es la única tarjeta con acento: su borde es ámbar y su
 * rótulo también, porque un producto sin rubro es algo que espera una decisión
 * (la misma señal que la píldora ámbar en el resto del sistema). Su bajada es el
 * enlace a asignarlos en lote, en azul de dato.
 */
export function PriceSummaryCards({ summary }: PriceSummaryCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Card
        label="Subieron de precio"
        value={summary.raised.count}
        sub={
          summary.raised.average_pct === null
            ? undefined
            : `Promedio ${formatVariation(summary.raised.average_pct)}`
        }
      />
      <Card
        label="Bajaron"
        value={summary.lowered.count}
        sub={
          summary.lowered.average_pct === null
            ? undefined
            : `Promedio ${formatVariation(summary.lowered.average_pct)}`
        }
      />
      <Card
        label="Nuevos sin rubro"
        value={summary.unclassified}
        accent
        action={{ href: '/rubros/sin-clasificar', label: 'Asignar en lote →' }}
      />
      <Card
        label="Dejaron de figurar"
        value={summary.discontinued}
        sub="Se conserva el último precio"
      />
    </div>
  )
}

interface CardProps {
  label: string
  value: number
  sub?: string
  /** La tarjeta que pide una decisión: borde y rótulo ámbar. */
  accent?: boolean
  action?: { href: string; label: string }
}

function Card({ label, value, sub, accent, action }: CardProps) {
  return (
    <div
      className={`rounded-xl border bg-card p-4 ${accent ? 'border-warn-border' : 'border-border'}`}
    >
      <div className={`section-label ${accent ? 'text-warn' : ''}`}>{label}</div>
      <div className="amount mt-2 text-2xl font-medium text-foreground">{value}</div>
      {sub && <div className="mt-2 text-xs text-muted-foreground">{sub}</div>}
      {action && (
        <Link
          className="mt-2 block text-xs font-medium text-link hover:underline"
          href={action.href}
        >
          {action.label}
        </Link>
      )}
    </div>
  )
}
