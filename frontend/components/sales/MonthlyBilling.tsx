import * as React from 'react'

import { BarChart, type Bar } from '@/components/common/BarChart'
import { Money } from '@/components/ui/amount'
import { Empty } from '@/components/ui/state'
import { count } from '@/lib/format'
import type { MonthTotal } from '@/lib/sales/types'
import { formatMonth } from '@/lib/time'

interface MonthlyBillingProps {
  months: MonthTotal[]
  /** Cuántos registros no entraron en ninguna barra. */
  excluded: number
  /** Lo que hay que saber de las ventas que hay detrás de las barras. */
  children?: React.ReactNode
}

/**
 * La facturación mes a mes (`RF-03`), con la forma de la guía visual (`3b`):
 * barras de tinta sobre la tarjeta, el mes abajo y la nota de lo excluido al
 * pie, en ámbar.
 *
 * La nota importa tanto como las barras. Un gráfico es una afirmación sobre el
 * negocio entero —«así viene el año»—, y sin ese renglón afirma también, en
 * silencio, que están todas las ventas adentro.
 */
export function MonthlyBilling({ months, excluded, children }: MonthlyBillingProps) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-base font-semibold text-foreground">Facturación mensual</h2>

      {months.length === 0 ? (
        <div className="mt-4">
          <Empty title="Todavía no hay ventas para mostrar." />
        </div>
      ) : (
        <div className="mt-5">
          <BarChart
            bars={months.map(toBar)}
            caption="Facturación por mes"
            valueLabel="Facturado"
            detailLabel="Ventas"
          />
        </div>
      )}

      {excluded > 0 && (
        <p className="mt-4 text-xs text-warn">
          {count(excluded)} registros excluidos no están en ninguna barra.
        </p>
      )}

      {children ? <div className="mt-3">{children}</div> : null}
    </section>
  )
}

/**
 * Un mes, listo para el gráfico.
 *
 * El año se escribe en enero y nada más: la serie arranca en 2023 y repetirlo
 * en las cuarenta barras es ruido, pero sin él nadie sabe de qué enero se
 * habla.
 */
function toBar(month: MonthTotal): Bar {
  const january = month.month.slice(5, 7) === '01'
  return {
    key: month.month,
    label: formatMonth(month.month, january),
    value: Number(month.total),
    reading: <Money value={month.total} as="span" />,
    detail: count(month.sales),
  }
}
