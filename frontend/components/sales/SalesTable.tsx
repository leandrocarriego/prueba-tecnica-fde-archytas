import { Code, Day, Money } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Empty } from '@/components/ui/state'
import { count } from '@/lib/format'
import type { Sale } from '@/lib/sales/types'

/**
 * El listado de ventas, con la forma de la lista de precios (guía visual `3k`).
 *
 * Cinco columnas: código, fecha, producto, cantidad y total. Es la misma tabla
 * que la de precios porque es la misma clase de pantalla —el padrón de algo, no
 * una bandeja de decisiones—, y dos listados del mismo producto que se dibujan
 * distinto se leen como dos productos.
 *
 * `showReason` agrega la columna del motivo, que sólo tiene sentido cuando lo
 * que se está mirando es lo que **no** suma: para una venta contada el motivo
 * está vacío, y una columna vacía en todas las filas es ruido.
 *
 * **Acá no hay nada que decidir.** Lo repetido y lo roto no está en esta lista:
 * está en «Para decidir», que es la única cola de pendientes de la plataforma.
 * Lo único que esta tabla marca es el valor **estimado**, y no como una decisión
 * sino como una advertencia sobre el número: RF-40 pide que todo lo que se
 * construya sobre un valor estimado diga que lo es, y una fila que lo esconde
 * hace que el total de la columna mienta sin que nadie se entere.
 */
export function SalesTable({ items, showReason = false }: { items: Sale[]; showReason?: boolean }) {
  if (items.length === 0) {
    return (
      <Empty title="No hay ventas que mostrar.">
        Probá con otras fechas, o esperá a la próxima extracción.
      </Empty>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <colgroup>
          <col className="w-[16%]" />
          <col className="w-[14%]" />
          <col className={showReason ? 'w-[20%]' : 'w-[30%]'} />
          <col className="w-[12%]" />
          <col className={showReason ? 'w-[18%]' : 'w-[28%]'} />
          {showReason && <col className="w-[20%]" />}
        </colgroup>
        <thead>
          <tr className="border-b border-border bg-muted">
            <th className="section-label px-4 py-2.5 text-left">Código</th>
            <th className="section-label px-4 py-2.5 text-left">Fecha</th>
            <th className="section-label px-4 py-2.5 text-left">Producto</th>
            <th className="section-label px-4 py-2.5 text-right">Cantidad</th>
            <th className="section-label px-4 py-2.5 text-right">Total</th>
            {showReason && <th className="section-label px-4 py-2.5 text-left">Por qué no suma</th>}
          </tr>
        </thead>
        <tbody>
          {items.map(sale => (
            <tr key={sale.id} className="border-b border-border align-middle">
              <Code value={sale.code} cell className="px-4 py-3 text-left" />
              <Day value={sale.sold_on} cell className="px-4 py-3 text-left" />
              <Code value={sale.product_code} cell className="px-4 py-3 text-left" />
              <td className="amount px-4 py-3 text-right">{count(sale.quantity)}</td>
              <td className="px-4 py-3 text-right">
                <Money value={sale.total} as="span" className="text-sm font-medium" />
                {/*
                  `RF-08`, `RF-40`: un valor que alguien estimó no está
                  confirmado, y se ve punteado sin leer la etiqueta.
                */}
                {sale.is_estimated && (
                  <Badge tone="draft" className="ml-2">
                    Estimada
                  </Badge>
                )}
              </td>
              {/*
                `RF-26`: un número que dice cuánto dejó afuera tiene que dejar
                ver **qué** dejó afuera, y con el motivo al lado. Sin esta
                columna la lista de lo excluido es una lista de filas sin
                explicación, que es peor que no tenerla.
              */}
              {showReason && (
                <td className="px-4 py-3 text-sm text-muted-foreground">{sale.reason ?? '—'}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
