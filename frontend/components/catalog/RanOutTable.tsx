import { Badge } from '@/components/ui/badge'
import { Code } from '@/components/ui/amount'
import { count } from '@/lib/format'
import type { StockCut } from '@/lib/sales/types'

/** Cuántos entran en la tarjeta antes de que deje de ser una lista y sea un listado. */
const SHOWN = 20

/**
 * Los productos que terminaron el período en cero (`RF-44`), con la forma de
 * tabla de la guía visual (`3b`): cabecera en versalita sobre papel, una fila
 * por producto y el código en mono.
 *
 * El código va en mono por lo mismo que la plata: dos códigos parecidos se
 * distinguen cuando los dígitos alinean.
 */
export function RanOutTable({ cuts }: { cuts: StockCut[] }) {
  if (cuts.length === 0) return null

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between gap-4 border-b border-border px-5 py-3.5">
        <h2 className="text-base font-semibold text-foreground">Se quedaron sin stock</h2>
        <Badge tone="warn">{count(cuts.length)} productos</Badge>
      </div>

      <table className="w-full">
        <thead>
          <tr className="border-b border-border bg-muted">
            <th className="section-label w-[22%] px-5 py-2.5 text-left">Código</th>
            <th className="section-label px-5 py-2.5 text-left">Producto</th>
          </tr>
        </thead>
        <tbody>
          {cuts.slice(0, SHOWN).map(cut => (
            <tr key={cut.product_id} className="border-b border-border last:border-0">
              <Code value={cut.code} cell className="px-5 py-3 text-left text-[13px]" />
              <td className="px-5 py-3 text-[13px] text-foreground">{cut.description}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {cuts.length > SHOWN && (
        <p className="border-t border-border px-5 py-3 text-xs text-muted-foreground">
          Se muestran los primeros {SHOWN} de {count(cuts.length)}.
        </p>
      )}
    </section>
  )
}
