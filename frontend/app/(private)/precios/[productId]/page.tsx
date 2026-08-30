import Link from 'next/link'
import { notFound } from 'next/navigation'

import { getSession } from '@/app/actions/auth'
import { CorrectionDialog } from '@/components/catalog/CorrectionDialog'
import { RevertCorrectionButton } from '@/components/catalog/RevertCorrectionButton'
import { FIELD_LABELS, markFor } from '@/lib/catalog/corrections'
import { formatDay, formatPrice, formatVariation, variationTone } from '@/lib/catalog/format'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { PriceHistory } from '@/lib/catalog/types'
import type { CorrectionReason } from '@/lib/operations/types'

/** Where a point came from, in words. */
const SOURCE_LABEL: Record<string, string> = {
  PORTAL: 'Publicado por el portal',
  SYSTEM: 'Registrado por el sistema',
}

/**
 * The screen of one product: what it is worth, how it got there, and what a
 * person changed about it.
 *
 * The price history has two origins and the page says which is which: the
 * points the portal already published when the product was first seen (RF-38 of
 * 001), and the changes the platform has seen since.
 *
 * Everything below that belongs to 003, and this is the screen the spec means
 * by "la pantalla de ese dato". A correction is shown with what the portal had
 * said (RF-27); a portal value that has since contradicted it is shown as a
 * question to settle here, because the spec is explicit that there is no
 * separate queue for conflicts (RF-28); undoing a correction is offered only
 * where there is one (RF-30, RF-33); and the datum's own history is one link
 * away, not on some other screen (RF-15).
 */
export default async function ProductPage({ params }: { params: Promise<{ productId: string }> }) {
  const { productId } = await params
  const history = await fetchFromApi<PriceHistory>(`/prices/${productId}/history`)

  if (history === null) notFound()

  // From the same place that validates a `reason_code`, so the list offered is
  // the list accepted. `null` when this session may not correct anything, and
  // then the screen simply does not offer it.
  const reasons = await fetchFromApi<CorrectionReason[]>('/operations/corrections/reasons')
  const session = await getSession()
  // Undoing is the owner's alone (RF-30). The backend refuses anybody else
  // regardless; this only keeps the screen from offering what it would refuse.
  const mayRevert = session !== null && canEdit(session.permissions, 'MANUAL_CORRECTIONS')
  const points = [...history.points].reverse()
  const correctedPrice = markFor(history.corrections, 'price')
  const correctedDescription = markFor(history.corrections, 'description')

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-8">
      <Link className="text-sm text-muted-foreground underline" href="/precios">
        « Volver a la lista de precios
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">{history.description}</h1>
        <p className="font-mono text-muted-foreground">{history.code}</p>
        {correctedDescription && (
          <p className="text-sm text-muted-foreground">
            Descripción corregida a mano · el portal decía «
            {String(correctedDescription.portal_value)}»
          </p>
        )}
      </header>

      <section className="flex flex-wrap gap-8 rounded border p-4">
        <div>
          <p className="text-sm text-muted-foreground">Precio vigente</p>
          <p className="text-2xl font-bold">{formatPrice(history.price)}</p>
          {correctedPrice && (
            <p className="text-sm text-muted-foreground">
              Corregido a mano · el portal decía{' '}
              {formatPrice(correctedPrice.portal_value as string)}
            </p>
          )}
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Contra el mes pasado</p>
          <p className={`text-2xl font-bold ${variationTone(history.monthly_variation_pct)}`}>
            {formatVariation(history.monthly_variation_pct)}
          </p>
        </div>
      </section>

      {history.corrections.some(correction => correction.status === 'CONFLICTED') && (
        <section className="space-y-2 rounded border border-red-300 bg-red-50 p-4">
          <h2 className="font-medium text-red-900">El portal informa otro valor</h2>
          {history.corrections
            .filter(correction => correction.status === 'CONFLICTED')
            .map(correction => (
              <p className="text-sm text-red-900" key={correction.correction_id}>
                Para {FIELD_LABELS[correction.field] ?? correction.field}, el portal había informado{' '}
                <strong>{String(correction.portal_value)}</strong>, quedó corregido a mano en{' '}
                <strong>{String(correction.corrected_value)}</strong>, y ahora informa{' '}
                <strong>{String(correction.conflict_value)}</strong>. La corrección sigue en pie:
                corregila otra vez si el valor nuevo es el bueno, o deshacela para volver a lo que
                dice el portal.
              </p>
            ))}
        </section>
      )}

      {reasons !== null && (
        <section className="space-y-3 rounded border p-4">
          <h2 className="text-lg font-medium">Corregir a mano</h2>
          <p className="text-sm text-muted-foreground">
            Lo que el portal informó se conserva siempre. Cada corrección queda registrada con tu
            nombre y el motivo.
          </p>
          <div className="space-y-3">
            <CorrectionDialog
              currentValue={history.price === null ? '' : String(history.price)}
              field="price"
              fieldLabel={FIELD_LABELS.price}
              numeric
              productId={history.product_id}
              reasons={reasons}
            />
            <CorrectionDialog
              currentValue={history.description}
              field="description"
              fieldLabel={FIELD_LABELS.description}
              productId={history.product_id}
              reasons={reasons}
            />
          </div>
          {history.corrections.length > 0 && (
            <ul className="space-y-2 border-t pt-3 text-sm">
              {history.corrections.map(correction => (
                <li className="flex flex-wrap items-center gap-3" key={correction.correction_id}>
                  <span>
                    {FIELD_LABELS[correction.field] ?? correction.field}: el portal decía{' '}
                    <strong>{String(correction.portal_value)}</strong>
                  </span>
                  {mayRevert && <RevertCorrectionButton correctionId={correction.correction_id} />}
                </li>
              ))}
            </ul>
          )}
          {/*
            Two links because the log keeps two data apart, and merging them on
            screen would hide which one changed: a price lives in
            `catalog.product_price` and a description in `catalog.product`.
          */}
          <p className="flex flex-wrap gap-4 border-t pt-3 text-sm">
            <Link
              className="underline underline-offset-2"
              href={`/historial?entidad=catalog.product_price&id=${history.product_id}`}
            >
              Historial de cambios del precio
            </Link>
            <Link
              className="underline underline-offset-2"
              href={`/historial?entidad=catalog.product&id=${history.product_id}`}
            >
              Historial de cambios del producto
            </Link>
          </p>
        </section>
      )}

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Evolución del precio</h2>
        {points.length === 0 ? (
          <p className="rounded border border-dashed p-6 text-center text-muted-foreground">
            Todavía no hay historial para este producto.
          </p>
        ) : (
          <div className="overflow-x-auto rounded border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left">
                <tr>
                  <th className="p-3 font-medium">Fecha</th>
                  <th className="p-3 text-right font-medium">Precio</th>
                  <th className="p-3 font-medium">Origen</th>
                </tr>
              </thead>
              <tbody>
                {points.map(point => (
                  <tr key={`${point.changed_at}-${point.price}`} className="border-t">
                    <td className="p-3">{formatDay(point.changed_at)}</td>
                    <td className="p-3 text-right font-medium">{formatPrice(point.price)}</td>
                    <td className="p-3 text-muted-foreground">
                      {SOURCE_LABEL[point.source] ?? point.source}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  )
}
