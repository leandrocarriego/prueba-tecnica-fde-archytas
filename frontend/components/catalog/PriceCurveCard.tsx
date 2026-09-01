import { BarChart, type Bar } from '@/components/common/BarChart'
import { Excluded } from '@/components/common/Excluded'
import { Money } from '@/components/ui/amount'
import { Empty } from '@/components/ui/state'
import { count } from '@/lib/format'
import type { PriceCurvePoint } from '@/lib/sales/types'
import { formatMonth } from '@/lib/time'

interface PriceCurveCardProps {
  curve: PriceCurvePoint[]
  excluded: number
}

/**
 * Cómo movió los precios el proveedor en el período (`RF-42`), con la forma de
 * la guía visual (`3b`).
 *
 * El aviso de lo que quedó afuera va **arriba del gráfico** por la misma razón
 * por la que va arriba de un importe: la barra de un mes con la mitad de los
 * productos sin precio se dibuja igual de alta que una completa.
 */
export function PriceCurveCard({ curve, excluded }: PriceCurveCardProps) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-base font-semibold text-foreground">Precio promedio del proveedor</h2>

      <div className="mt-4 space-y-4">
        <Excluded howMany={excluded}>
          No entran en la curva: les falta el precio o la fecha con que compararlos.
        </Excluded>

        {curve.length === 0 ? (
          <Empty title="Todavía no hay historial de precios en este período." />
        ) : (
          <BarChart
            bars={curve.map(toBar)}
            caption="Precio promedio del proveedor por mes"
            valueLabel="Precio promedio"
            detailLabel="Cambios"
          />
        )}
      </div>

      <p className="mt-4 text-xs text-muted-foreground">
        {excluded === 0
          ? 'No se excluyó ningún producto de este corte.'
          : `${count(excluded)} productos excluidos.`}
      </p>
    </section>
  )
}

/** Un mes de la curva, listo para el gráfico. */
function toBar(point: PriceCurvePoint): Bar {
  const january = point.month.slice(5, 7) === '01'
  return {
    key: point.month,
    label: formatMonth(point.month, january),
    value: Number(point.average_price),
    reading: <Money value={point.average_price} as="span" />,
    detail: count(point.changes),
  }
}
