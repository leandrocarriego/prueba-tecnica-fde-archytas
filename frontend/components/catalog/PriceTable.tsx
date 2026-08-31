import Link from 'next/link'

import { FIELD_NOUNS, isConflicted, markFor } from '@/lib/catalog/corrections'
import { formatMoment, formatPrice, formatVariation, variationTone } from '@/lib/catalog/format'
import type { Price } from '@/lib/catalog/types'

interface PriceTableProps {
  items: Price[]
}

/**
 * What a correction carries, narrowed to what `formatPrice` can read.
 *
 * The generated schema types these values `unknown`, and rightly: a correction
 * row holds whatever the field it corrects held, and the same column serves a
 * price, a currency and a description. `formatPrice` takes an amount, so the
 * question gets asked instead of asserted — asserting `as string` would promise
 * the compiler a shape nothing checked, and the day the API sends anything else
 * the table writes «$ NaN» where a price should be: `Number.isNaN` does not
 * coerce, so whatever arrived walks straight past the formatter's own guard and
 * into `Intl`. Asked, it renders the «—» that guard reserves for a value it
 * cannot read.
 */
function amount(value: unknown): string | number | null {
  return typeof value === 'string' || typeof value === 'number' ? value : null
}

/**
 * The price list in force (RF-04).
 *
 * A Server Component: it renders data and has no interactivity of its own, so
 * there is no reason to ship it to the browser.
 *
 * Four marks earn their place in the table. A **rise above the threshold** is
 * what the owner asked to see without reading a hundred rows (RF-25), and a
 * product that **did not come in the last list** says so next to the price it
 * is still showing, instead of looking as fresh as the rest (RF-08).
 *
 * The other two come from 003. A **corrected** price is told apart at a glance
 * and carries what the portal had said right beside it (RF-26, RF-27) — a
 * number nobody can explain is worth less than a number that is slightly off.
 * And when the portal has since reported something else, the row says **so**
 * instead of quietly applying it (RF-28): the correction stands until a person
 * decides, and this is where they find out there is something to decide.
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
          {items.map(item => {
            const corrected = markFor(item.corrections, 'price')
            // Every contradicted field, not just the price. The row carries the
            // marks of all three correctable fields, and reading only one of
            // them was how a contradicted **description** reached this screen
            // saying nothing at all (RF-26, RF-28).
            const contradicted = item.corrections.filter(isConflicted)
            return (
              <tr
                key={item.product_id}
                className={`border-t ${item.is_highlighted ? 'bg-warn-surface' : ''}`}
              >
                <td className="p-3 font-mono">
                  <Link
                    className="underline underline-offset-2"
                    href={`/precios/${item.product_id}`}
                  >
                    {item.code}
                  </Link>
                </td>
                <td className="p-3">
                  {item.description}
                  {item.is_highlighted && (
                    <span className="ml-2 rounded bg-warn-border px-2 py-0.5 text-xs text-warn">
                      Subió fuerte
                    </span>
                  )}
                  {item.is_stale && (
                    <span className="ml-2 rounded bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
                      No vino en la última lista
                    </span>
                  )}
                  {/*
                    Keyed by the field, and the row cannot carry two marks of
                    one: the backend's `CORRECTABLE_FIELDS` maps each field to
                    exactly one entity, and the database holds a partial unique
                    index over `(entity_type, entity_id, field)` covering every
                    correction that is not `REVERTED` — which is precisely the
                    set `corrections_in_force` selects. A second mark for the
                    same field is not something this list happens not to see: it
                    is a row the database will not accept.
                  */}
                  {contradicted.map(mark => (
                    <span
                      className="ml-2 rounded bg-danger-surface px-2 py-0.5 text-xs text-danger"
                      key={mark.field}
                    >
                      {mark.field === 'price'
                        ? `El portal informa ${formatPrice(amount(mark.conflict_value))}`
                        : `El portal informa otra ${FIELD_NOUNS[mark.field] ?? mark.field}`}
                    </span>
                  ))}
                </td>
                <td className="p-3 text-right font-medium">
                  {formatPrice(item.price)}
                  {corrected && (
                    <span className="block text-xs font-normal text-muted-foreground">
                      Corregido a mano · el portal decía{' '}
                      {formatPrice(amount(corrected.portal_value))}
                    </span>
                  )}
                </td>
                <td className="p-3 text-right text-muted-foreground">
                  {formatPrice(item.previous_price)}
                </td>
                <td className={`p-3 text-right ${variationTone(item.monthly_variation_pct)}`}>
                  {formatVariation(item.monthly_variation_pct)}
                </td>
                <td className="p-3 text-muted-foreground">{formatMoment(item.effective_at)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
