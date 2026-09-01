import Link from 'next/link'
import { notFound } from 'next/navigation'

import { getSession } from '@/app/actions/auth'
import { CorrectionDialog } from '@/components/catalog/CorrectionDialog'
import { RevertCorrectionButton } from '@/components/catalog/RevertCorrectionButton'
import { FIELD_LABELS, markFor } from '@/lib/catalog/corrections'
import { formatDay, formatPrice, formatVariation, variationTone } from '@/lib/catalog/format'
import { readFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { PriceHistory } from '@/lib/catalog/types'
import type { CorrectionReason } from '@/lib/operations/types'
import { Empty, ErrorState } from '@/components/ui/state'
import { Code } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Notice } from '@/components/ui/notice'
import { isUnconfirmedPrice, pill } from '@/lib/ui/tone'

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
  const session = await getSession()
  const read = await readFromApi<PriceHistory>(`/prices/${productId}/history`)

  if (!read.ok) {
    // `GET /prices/{id}/history` is open to every authenticated role, so there
    // is no refusal to tell apart here: either the product is not there, or
    // the API did not answer. Saying "no existe" over an outage would tell
    // somebody their product was deleted.
    if (read.failure === 'missing') notFound()
    return (
      <div className="space-y-6">
        <Link className="text-sm text-link hover:underline" href="/precios">
          « Volver a la lista de precios
        </Link>
        <ErrorState title="No pudimos traer este producto.">
          Probá de nuevo en unos minutos.
        </ErrorState>
      </div>
    )
  }

  const history = read.data
  // Correcting a product is for whoever may write the catalog (RF-21, RF-24):
  // `POST /catalog/products/{id}/corrections` asks for PRODUCT_CATALOG in
  // writing, which purchasing does not have. The backend refuses anybody else
  // regardless; this only keeps the screen from offering a button that answers
  // 403. The list of reasons would not have said so — it is served to every
  // authenticated role, because it is what validates a `reason_code`.
  const mayCorrect = session !== null && canEdit(session.permissions, 'PRODUCT_CATALOG')
  // Undoing is the owner's alone (RF-30), and it is a different section from
  // correcting: whoever may correct is not necessarily who may undo.
  const mayRevert = session !== null && canEdit(session.permissions, 'MANUAL_CORRECTIONS')
  // Asked for only when it is going to be offered: the list is the API's
  // because the API is what validates a `reason_code`, and a list nobody will
  // see is a round trip nobody needs.
  const reasons = mayCorrect
    ? await readFromApi<CorrectionReason[]>('/operations/corrections/reasons')
    : null
  const points = [...history.points].reverse()
  const correctedPrice = markFor(history.corrections, 'price')
  const correctedDescription = markFor(history.corrections, 'description')

  return (
    <div className="space-y-6">
      <Link className="text-sm text-link hover:underline" href="/precios">
        « Volver a la lista de precios
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">{history.description}</h1>
        <Code value={history.code} as="div" className="text-muted-foreground" />
        {correctedDescription && (
          <p className="text-sm text-muted-foreground">
            Descripción corregida a mano · el portal decía «
            {String(correctedDescription.portal_value)}»
          </p>
        )}
      </header>

      <Card className="flex flex-wrap gap-8 p-5">
        <div>
          <p className="text-sm text-muted-foreground">Precio vigente</p>
          <p className="amount text-2xl font-bold">{formatPrice(history.price)}</p>
          {correctedPrice && (
            <p className="text-sm text-muted-foreground">
              Corregido a mano · el portal decía{' '}
              {formatPrice(correctedPrice.portal_value as string)}
            </p>
          )}
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Contra el mes pasado</p>
          <p
            className={`amount text-2xl font-bold ${variationTone(history.monthly_variation_pct)}`}
          >
            {formatVariation(history.monthly_variation_pct)}
          </p>
        </div>
      </Card>

      {history.corrections.some(correction => correction.status === 'CONFLICTED') && (
        <Notice tone="danger" title="El portal informa otro valor">
          {history.corrections
            .filter(correction => correction.status === 'CONFLICTED')
            .map(correction => (
              <p key={correction.correction_id}>
                Para {FIELD_LABELS[correction.field] ?? correction.field}, el portal había informado{' '}
                <strong>{String(correction.portal_value)}</strong>, quedó corregido a mano en{' '}
                <strong>{String(correction.corrected_value)}</strong>, y ahora informa{' '}
                <strong>{String(correction.conflict_value)}</strong>. La corrección sigue en pie:
                corregila otra vez si el valor nuevo es el bueno, o deshacela para volver a lo que
                dice el portal.
              </p>
            ))}
        </Notice>
      )}

      {/*
        `id` so a link can land here and not at the top of the page. The review
        queue sends people to it by name: a load refused by a correction in
        force says the correction has to be changed for the amount to move, and
        this is where that is done — correcting it again, which is what leaves
        another value in force. An anchor and not a route, because the block is
        one section of the product's own screen and pulling it into a page of
        its own would split the correction from the value it is about.
      */}
      {mayCorrect && (
        <Card className="space-y-3 p-5" id="correcciones">
          <h2 className="text-lg font-medium">Corregir a mano</h2>
          <p className="text-sm text-muted-foreground">
            Lo que el portal informó se conserva siempre. Cada corrección queda registrada con tu
            nombre y el motivo.
          </p>
          {reasons !== null && reasons.ok ? (
            <div className="space-y-3">
              <CorrectionDialog
                currentValue={history.price === null ? '' : String(history.price)}
                field="price"
                fieldLabel={FIELD_LABELS.price}
                numeric
                productId={history.product_id}
                reasons={reasons.data}
              />
              <CorrectionDialog
                currentValue={history.description}
                field="description"
                fieldLabel={FIELD_LABELS.description}
                productId={history.product_id}
                reasons={reasons.data}
              />
            </div>
          ) : (
            /*
              Without the reasons there is no correction to make: the reason is
              required and the API validates it against this very list. So the
              screen says the part that failed, and keeps everything below.
            */
            <ErrorState title="No pudimos traer los motivos de corrección.">
              Probá de nuevo en unos minutos.
            </ErrorState>
          )}
        </Card>
      )}

      {/*
        What was already corrected is not an action: it is what the datum says
        about itself, and anybody who reaches this screen may read it (RF-26,
        RF-27). Only the button that undoes is the owner's (RF-30).
      */}
      {history.corrections.length > 0 && (
        <Card className="space-y-3 p-5">
          <h2 className="text-lg font-medium">Corregido a mano</h2>
          <ul className="space-y-2 text-sm">
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
        </Card>
      )}

      {/*
        Two links because the log keeps two data apart, and merging them on
        screen would hide which one changed: a price lives in
        `catalog.product_price` and a description in `catalog.product`.
      */}
      <p className="flex flex-wrap gap-4 text-sm">
        <Link
          className="text-link hover:underline"
          href={`/historial?entidad=catalog.product_price&id=${history.product_id}`}
        >
          Historial de cambios del precio
        </Link>
        <Link
          className="text-link hover:underline"
          href={`/historial?entidad=catalog.product&id=${history.product_id}`}
        >
          Historial de cambios del producto
        </Link>
      </p>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Evolución del precio</h2>
        {points.length === 0 ? (
          <Empty title="Todavía no hay historial para este producto." />
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border bg-card">
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
                    <Code value={formatDay(point.changed_at)} cell className="p-3 text-left" />
                    <td className="amount p-3 text-right font-medium">
                      {formatPrice(point.price)}
                    </td>
                    <td className="p-3">
                      {/*
                       * `RF-08`: un precio que puso la plataforma y que el
                       * portal no publicó va punteado.
                       */}
                      <Badge tone={pill('neutral', isUnconfirmedPrice(point.source))}>
                        {SOURCE_LABEL[point.source] ?? point.source}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
