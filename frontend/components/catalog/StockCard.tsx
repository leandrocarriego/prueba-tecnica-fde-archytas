import { Excluded } from '@/components/common/Excluded'
import { Share } from '@/components/common/Share'
import { count } from '@/lib/format'

interface StockCardProps {
  /** Productos con foto en al menos una punta del período: los que entran. */
  compared: number
  /** Productos sin ninguna foto con que comparar: los que quedan afuera. */
  excluded: number
  /** De los comparados, cuántos terminaron el período en cero (`RF-44`). */
  ranOut: number
}

/**
 * Qué parte del catálogo pudo entrar al corte de stock (`RF-43`, `RF-44`), con
 * la forma que la guía visual (`3b`) usa para una composición: un renglón por
 * parte, el número a la derecha y la barra debajo.
 *
 * Lo que excluye el corte es **no tener ninguna foto** que comparar —ni una
 * desde el inicio del período, ni una hasta el final—, no que falte en una de
 * las dos puntas: con una sola observación la misma foto es la de apertura y la
 * de cierre, y el producto entra al corte leyéndose como «no se movió».
 *
 * Los excluidos van rayados y no de un color liso: son una porción que se mide
 * pero **no está sumada** en el número de al lado. Un liso más se leería como
 * una categoría más del catálogo.
 */
export function StockCard({ compared, excluded, ranOut }: StockCardProps) {
  const total = compared + excluded

  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-base font-semibold text-foreground">Stock</h2>

      <div className="mt-4 space-y-4">
        <Excluded howMany={excluded}>
          Quedaron afuera porque no hay ninguna foto de su stock con que comparar en este período.
          No se cuentan como cero: decir cero sería inventar un stock.
        </Excluded>

        {total === 0 ? (
          <p className="text-sm text-muted-foreground">
            Todavía no hay productos activos para comparar en este período.
          </p>
        ) : (
          <div className="space-y-3">
            <Share
              label="Con stock comparable"
              reading={count(compared)}
              share={(compared / total) * 100}
            />
            <Share
              label="Sin ninguna foto"
              reading={count(excluded)}
              share={(excluded / total) * 100}
              excluded
            />
          </div>
        )}
      </div>

      <p className="mt-4 text-xs text-warn">
        {ranOut === 0
          ? 'Ningún producto terminó el período sin stock.'
          : ranOut === 1
            ? '1 producto terminó el período sin stock.'
            : `${count(ranOut)} productos terminaron el período sin stock.`}
      </p>
    </section>
  )
}
