import Link from 'next/link'

import { count } from '@/lib/format'
import type { SalesDashboard } from '@/lib/sales/types'

/**
 * Qué le pasó a las ventas que hay detrás de las barras: cuántas están
 * apartadas, cuántos grupos de repetidas esperan una decisión y cuántas unificó
 * el sistema solo (`RF-12`, `RF-14`).
 *
 * Va al pie del gráfico y no en una tarjeta propia porque es **sobre** el
 * gráfico: son las ventas que no están en ninguna barra, o que están una sola
 * vez habiendo llegado dos. Arriba, la fila de tarjetas es del negocio —lo
 * facturado, lo que se debe, lo que vence—; esto es sobre la calidad del dato
 * con que se dibujó.
 *
 * Los tres se dicen siempre, también en cero. «Ninguna apartada» es una
 * respuesta; que el renglón desaparezca no lo es.
 */
export function SalesQuality({ sales }: { sales: SalesDashboard }) {
  return (
    <p className="text-xs text-muted-foreground">
      {sales.held_total > 0 ? (
        <Link className="font-medium text-link hover:underline" href="/ventas/revision">
          {count(sales.held_total)} ventas apartadas →
        </Link>
      ) : (
        'Ninguna venta apartada'
      )}
      {' · '}
      {sales.pending_groups === 0
        ? 'ningún grupo de repetidas sin resolver'
        : `${count(sales.pending_groups)} grupos de repetidas sin resolver`}
      {' · '}
      {sales.invoiced.merged === 0
        ? 'ninguna repetida unificada sola'
        : `${count(sales.invoiced.merged)} repetidas idénticas unificadas solas`}
      .
    </p>
  )
}
