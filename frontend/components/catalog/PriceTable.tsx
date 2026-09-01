import Link from 'next/link'

import { FIELD_NOUNS, isConflicted, markFor } from '@/lib/catalog/corrections'
import { formatPrice, formatVariation } from '@/lib/catalog/format'
import type { Price } from '@/lib/catalog/types'
import { Empty } from '@/components/ui/state'
import { Money } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'

interface PriceTableProps {
  items: Price[]
}

/**
 * What a correction carries, narrowed to what `formatPrice` can read.
 *
 * The generated schema types these values `unknown`, and rightly: a correction
 * row holds whatever the field it corrects held. `formatPrice` takes an amount,
 * so the question gets asked instead of asserted — the day the API sends
 * anything else the formatter renders «—» rather than «$ NaN».
 */
function amount(value: unknown): string | number | null {
  return typeof value === 'string' || typeof value === 'number' ? value : null
}

/**
 * The percentage between the price in force and the one before it, or `null`
 * when there is nothing to compare against.
 *
 * This is the column the design calls VARIACIÓN: the move between the last two
 * lists (price vs `previous_price`), not the month-over-month figure that lives
 * on the product's own page. Both numbers are real; this is the one the table
 * draws beside ANTERIOR so the two columns tell one story.
 */
function variationFrom(price: string | null, previous: string | null): number | null {
  if (price === null || previous === null) return null
  const now = Number(price)
  const before = Number(previous)
  if (Number.isNaN(now) || Number.isNaN(before) || before === 0) return null
  return ((now - before) / before) * 100
}

/**
 * La lista de precios en vigencia (RF-04), con la forma de la guía visual (`3k`).
 *
 * Cinco columnas: producto, rubro, precio hoy, anterior y variación. El rubro
 * viaja en la misma fila que el precio; «Sin rubro» se pinta ámbar porque es una
 * de las cosas que esperan una decisión.
 *
 * Cuatro marcas siguen ganando su lugar. Una **suba fuerte** tiñe la fila
 * (RF-25). Un producto que **no vino en la última lista** lo dice al lado del
 * precio que sigue mostrando (RF-08). Un precio **corregido** a mano se
 * distingue y lleva lo que el portal había dicho (RF-26, RF-27); y cuando el
 * portal informó otra cosa desde entonces, la fila lo dice en vez de aplicarlo
 * solo (RF-28).
 */
export function PriceTable({ items }: PriceTableProps) {
  if (items.length === 0) {
    return (
      <Empty title="No hay productos que coincidan.">
        Probá con otra búsqueda, o quitá los filtros.
      </Empty>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <colgroup>
          <col className="w-[36%]" />
          <col className="w-[18%]" />
          <col className="w-[16%]" />
          <col className="w-[16%]" />
          <col className="w-[14%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-border bg-muted">
            <th className="section-label px-4 py-2.5 text-left">Producto</th>
            <th className="section-label px-4 py-2.5 text-left">Rubro</th>
            <th className="section-label px-4 py-2.5 text-left">Precio hoy</th>
            <th className="section-label px-4 py-2.5 text-left">Anterior</th>
            <th className="section-label px-4 py-2.5 text-left">Variación</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => {
            const corrected = markFor(item.corrections, 'price')
            // Every contradicted field, not just the price: reading only one of
            // them was how a contradicted **description** reached this screen
            // saying nothing at all (RF-26, RF-28).
            const contradicted = item.corrections.filter(isConflicted)
            const isNew = item.previous_price === null
            const variation = variationFrom(item.price, item.previous_price)
            return (
              <tr
                key={item.product_id}
                className={`border-b border-border align-middle ${
                  item.is_highlighted ? 'bg-warn-surface' : ''
                }`}
              >
                <td className="px-4 py-3">
                  <Link
                    className="text-sm text-foreground hover:text-link hover:underline"
                    href={`/precios/${item.product_id}`}
                  >
                    {item.description}
                  </Link>
                  {item.is_highlighted && (
                    <Badge tone="warn" className="ml-2">
                      Subió fuerte
                    </Badge>
                  )}
                  {item.is_stale && <Badge className="ml-2">No vino en la última lista</Badge>}
                  {/*
                    Keyed by the field, and the row cannot carry two marks of
                    one: the database holds a partial unique index over
                    `(entity_type, entity_id, field)`. A second mark for the same
                    field is a row the database will not accept.
                  */}
                  {contradicted.map(mark => (
                    <Badge tone="danger" className="ml-2" key={mark.field}>
                      {mark.field === 'price'
                        ? `El portal informa ${formatPrice(amount(mark.conflict_value))}`
                        : `El portal informa otra ${FIELD_NOUNS[mark.field] ?? mark.field}`}
                    </Badge>
                  ))}
                </td>
                <td className="px-4 py-3">
                  {item.category_name === null ? (
                    <Badge tone="warn">Sin rubro</Badge>
                  ) : (
                    <Badge>{item.category_name}</Badge>
                  )}
                </td>
                <td className="px-4 py-3">
                  <Money value={item.price} as="span" className="text-sm font-medium" />
                  {corrected && (
                    <span className="block text-xs font-normal text-muted-foreground">
                      Corregido · el portal decía {formatPrice(amount(corrected.portal_value))}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {isNew ? (
                    <span className="text-sm text-muted-ink">nuevo</span>
                  ) : (
                    <Money
                      value={item.previous_price}
                      as="span"
                      className="text-sm text-muted-ink"
                    />
                  )}
                </td>
                <td className="px-4 py-3">
                  <VariationCell isNew={isNew} variation={variation} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

/** La celda de variación: píldora ámbar si subió, verde si bajó, «=» si no se movió. */
function VariationCell({ isNew, variation }: { isNew: boolean; variation: number | null }) {
  if (isNew) return <Badge tone="info">Nuevo</Badge>
  if (variation === null) return <span className="text-sm text-muted-ink">—</span>
  if (Math.round(variation * 10) === 0) return <span className="text-sm text-muted-ink">=</span>
  return <Badge tone={variation > 0 ? 'warn' : 'ok'}>{formatVariation(variation)}</Badge>
}
