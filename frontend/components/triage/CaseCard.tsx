'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

import { resolveCase } from '@/app/actions/triage'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useToast } from '@/components/ui/toast'
import { formatMoment, formatPrice } from '@/lib/catalog/format'
import type { Category } from '@/lib/catalog/types'
import { ACKNOWLEDGE_ONLY_KINDS, caseKindLabel, type Case } from '@/lib/triage/types'

interface CaseCardProps {
  item: Case
  /**
   * Whether this person may change a correction, which is a different question
   * from whether they may empty this queue. Resolving a case is `PRICES` in
   * writing — the owner and purchasing; correcting a value is `PRODUCT_CATALOG`
   * in writing — the owner and sales. So purchasing reaches this screen and
   * cannot take that door, and offering it anyway would be a link that answers
   * 403. Whoever cannot take it is told who can, rather than left in front of
   * an instruction with nobody attached to it.
   */
  mayCorrect: boolean
  /**
   * Los rubros con los que se resuelve un caso `unknown_category` (RF-14 de
   * 010). Los pasa la pantalla: esta tarjeta es de `triage` y pedirlos ella
   * misma la ataría al catálogo, que es de otro módulo y de otro dominio.
   */
  categories: Category[]
}

function payloadText(item: Case, key: string): string {
  const value = item.payload[key]
  return typeof value === 'string' || typeof value === 'number' ? String(value) : ''
}

/** The correction a refusal is about: where to look at it, and who made it. */
interface RefusedByCorrection {
  productId: number
  correctedBy: string | null
}

/**
 * That correction, when the refusal was about one.
 *
 * Hung on `correction_id`, which only this refusal carries, and not on
 * `product_id`, which several carry. Deciding by the product would light the
 * links up under refusals that have nothing to do with a correction — a
 * `missing_product` case whose product a revoked rule removed answers 404 with
 * a `product_id` in it, and the card would offer «Ver la corrección» for a
 * correction that does not exist, on a page that answers 404 too.
 *
 * `details` is whatever the backend put in the envelope, so every key is asked
 * rather than trusted. A refusal with nothing in it — the session expired, the
 * API did not answer — leaves the message on its own, which is still the whole
 * of what RF-22 asks for.
 */
function refusedByCorrection(
  details: Record<string, unknown> | undefined
): RefusedByCorrection | null {
  if (typeof details?.correction_id !== 'number') return null
  const productId = details.product_id
  if (typeof productId !== 'number') return null
  const correctedBy = details.corrected_by_name
  return { productId, correctedBy: typeof correctedBy === 'string' ? correctedBy : null }
}

/**
 * One case in the review queue, with the decision its kind admits.
 *
 * A Client Component: resolving is the interaction this screen exists for. Each
 * kind offers exactly the decisions the spec names, so the person is never
 * asked to type what the system already knows — RF-30 for an unknown product,
 * RF-31 for one that stopped coming, RF-29 for a row nobody could read.
 *
 * How it went is read in two different places, and the split is the same one
 * `RevertCorrectionButton` makes for the same reason (RF-22 of 003, which is
 * the feature that published resolving a case as a manual action). A refusal
 * leaves this card where it was, so its message goes inside it, over the case
 * that was not resolved — there is one card per pending case, and a message off
 * in a corner would not say which one failed. Deciding takes the card away:
 * `/revision` lists only what is still pending, so the refreshed page drops
 * this case and unmounts the component along with anything it had written in
 * its own state. That confirmation is announced to the toaster in the root
 * layout, which is the only thing still on screen once the card is gone.
 */
export function CaseCard({ item, mayCorrect, categories }: CaseCardProps) {
  const router = useRouter()
  const { addToast } = useToast()
  const [price, setPrice] = useState(payloadText(item, 'price'))
  const [categoryId, setCategoryId] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Kept beside the message and not folded into it: a refusal about a
  // correction turns into a link and a name, and rewriting the sentence here to
  // slip either one inside it would be this component editing text the backend
  // wrote.
  const [refused, setRefused] = useState<RefusedByCorrection | null>(null)

  async function decide(decision: Record<string, unknown>) {
    setSaving(true)
    setError(null)
    setRefused(null)
    const result = await resolveCase(item.id, decision)
    setSaving(false)
    if (result.ok) {
      addToast({
        type: 'success',
        title: 'Caso resuelto',
        description: 'La decisión quedó registrada y el caso sale de la cola.',
      })
      router.refresh()
      return
    }
    setError(result.message)
    setRefused(refusedByCorrection(result.details))
  }

  return (
    <article className="space-y-3 rounded border p-4">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="text-sm text-muted-foreground">{caseKindLabel(item.kind)}</p>
          <h3 className="font-medium">{item.reason}</h3>
        </div>
        <div className="text-right text-sm text-muted-foreground">
          <p>
            {formatMoment(item.created_at)}
            {item.occurrences > 1 && ` · se repitió ${item.occurrences} veces`}
          </p>
          {/*
            Cuánto hace que espera, y si eso ya es demasiado (RF-16, RF-17). El
            número lo calcula el backend contra el parámetro que el dueño mueve
            (RF-18), así que la pantalla no decide nada acá: lo muestra.
          */}
          {item.status === 'PENDING' && (
            <p className={item.is_stale ? 'font-medium text-warn' : undefined}>
              {item.waiting_days === 0
                ? 'Llegó hoy'
                : `Espera hace ${item.waiting_days} ${item.waiting_days === 1 ? 'día' : 'días'}`}
              {item.is_stale && ' · demorado'}
            </p>
          )}
        </div>
      </header>

      <dl className="grid gap-1 text-sm sm:grid-cols-2">
        {payloadText(item, 'product_code') && (
          <div>
            <dt className="inline text-muted-foreground">Código: </dt>
            <dd className="inline font-mono">{payloadText(item, 'product_code')}</dd>
          </div>
        )}
        {payloadText(item, 'description') && (
          <div>
            <dt className="inline text-muted-foreground">Descripción: </dt>
            <dd className="inline">{payloadText(item, 'description')}</dd>
          </div>
        )}
        {payloadText(item, 'price') && (
          <div>
            <dt className="inline text-muted-foreground">Precio que trajo la lista: </dt>
            <dd className="inline">{formatPrice(payloadText(item, 'price'))}</dd>
          </div>
        )}
        {payloadText(item, 'category_text') && (
          <div>
            <dt className="inline text-muted-foreground">Forma escrita: </dt>
            <dd className="inline font-mono">{payloadText(item, 'category_text')}</dd>
          </div>
        )}
        {/*
          De qué pantalla del portal salió y cuándo se leyó (RF-11). Es lo que
          evita que resolver un pendiente empiece por salir a buscar el dato, y
          desde la 011 lo traen **todas** las clases: el requisito dice «cada
          pendiente», y uno solo que no lo dijera obligaría a quien mira la
          lista a saber de antemano cuáles lo traen.

          Se sigue dibujando condicionado por dos razones que no son la misma:
          los pendientes abiertos antes de esta corrección no tienen el dato en
          su `payload` y nadie se lo va a inventar hacia atrás, y un rubro que
          volvió a la cola porque alguien revocó su regla no salió de ninguna
          lectura, así que no dice cuándo se leyó.
        */}
        {payloadText(item, 'origin') && (
          <div>
            <dt className="inline text-muted-foreground">Salió de: </dt>
            <dd className="inline">{payloadText(item, 'origin')}</dd>
          </div>
        )}
        {payloadText(item, 'read_at') && (
          <div>
            <dt className="inline text-muted-foreground">Se leyó: </dt>
            <dd className="inline">{formatMoment(payloadText(item, 'read_at'))}</dd>
          </div>
        )}
        {payloadText(item, 'excerpt') && (
          <div className="sm:col-span-2">
            <dt className="text-muted-foreground">Lo que decía la fila:</dt>
            <dd className="mt-1 overflow-x-auto rounded bg-muted/50 p-2 font-mono text-xs">
              {payloadText(item, 'excerpt')}
            </dd>
          </div>
        )}
      </dl>

      <div className="flex flex-wrap items-center gap-2">
        {item.kind === 'unknown_product' && (
          <>
            <Button disabled={saving} onClick={() => decide({ action: 'incorporate' })}>
              Incorporarlo al catálogo
            </Button>
            <Button
              variant="outline"
              disabled={saving}
              onClick={() => decide({ action: 'ignore' })}
            >
              Dejarlo fuera
            </Button>
          </>
        )}

        {item.kind === 'missing_product' && (
          <>
            <Button disabled={saving} onClick={() => decide({ action: 'discontinue' })}>
              Darlo por discontinuado
            </Button>
            <Button variant="outline" disabled={saving} onClick={() => decide({ action: 'keep' })}>
              Mantenerlo vigente
            </Button>
          </>
        )}

        {item.kind === 'unreadable_row' && (
          <>
            <Input
              className="max-w-40"
              type="number"
              min={0}
              placeholder="Precio"
              value={price}
              onChange={event => setPrice(event.target.value)}
            />
            <Button
              disabled={saving || price === ''}
              onClick={() => decide({ product_code: payloadText(item, 'product_code'), price })}
            >
              Registrar este precio
            </Button>
          </>
        )}

        {item.kind === 'unknown_category' && (
          /*
            RF-14 de la 010: la forma escrita que nadie decidió se resuelve
            **acá**, en la misma pantalla donde compras ya resuelve todo lo que
            la actualización aparta. Hasta ahora el caso llegaba a esta cola y
            la tarjeta no sabía dibujarlo: se veía el `kind` crudo, sin la forma
            escrita y sin ningún control para asignarle un rubro.

            `remember: true` va fijo y no es un detalle: es lo que convierte la
            decisión en una equivalencia guardada, y con eso la misma forma
            escrita no se vuelve a preguntar y los productos que la esperaban
            quedan clasificados (RF-24 y RF-25 de la 008).
          */
          <>
            <select
              className="rounded border px-2 py-1 text-sm"
              value={categoryId}
              onChange={event => setCategoryId(event.target.value)}
            >
              <option value="">Elegí un rubro…</option>
              {categories.map(category => (
                <option key={category.id} value={String(category.id)}>
                  {category.name}
                </option>
              ))}
            </select>
            <Button
              disabled={saving || categoryId === ''}
              onClick={() => decide({ category_id: Number(categoryId) })}
            >
              Asignar este rubro
            </Button>
          </>
        )}

        {item.kind === 'unreadable_history' && (
          <Button disabled={saving} onClick={() => decide({ action: 'ignore' })}>
            Dar el historial por revisado
          </Button>
        )}

        {/*
          Las seis clases que sólo se pueden dar por revisadas: facturas (004),
          órdenes (007) y las cuatro que agrega la 011 —padrón, comprobantes,
          buzón y ventas—. Una factura, una orden o una venta nacen de una fila
          que el portal publicó, y cargarlas a mano desde acá es exactamente lo
          que la spec firmada dejó fuera de alcance.

          Estaban escritas una por una, con el mismo botón repetido, y con
          cuatro más eso pasa de repetición a copia. Lo que las junta no es que
          se parezcan: es que comparten el motivo —el origen es de sólo lectura—
          y ese motivo está escrito una vez, en `ACKNOWLEDGE_ONLY_KINDS`.

          Lo que la cola aporta es que **existan**: hasta la 011, cuatro de las
          seis se perdían en silencio.
        */}
        {ACKNOWLEDGE_ONLY_KINDS.includes(item.kind) && (
          <Button disabled={saving} onClick={() => decide({ action: 'ignore' })}>
            Darlo por revisado
          </Button>
        )}
      </div>

      {/*
        The refusal, then who is behind it, then where to go about it. The card
        stays exactly where it was — the case was not resolved, so `/revision`
        still lists it — and the amount the person typed is still in the field
        above, which is the difference between being told and being sent back to
        the start.

        Whoever may not change a correction is told who may, instead of being
        left in front of an instruction with nobody attached to it: the message
        says the correction has to be changed, and purchasing — who empties this
        queue — cannot change one. Hiding the link and saying nothing else would
        be half the decision.
      */}
      {error && (
        <div className="space-y-2 text-sm">
          <p className="text-danger">{error}</p>
          {refused !== null && (
            <>
              {refused.correctedBy !== null && (
                <p className="text-danger">La corrección la hizo {refused.correctedBy}.</p>
              )}
              <p className="flex flex-wrap gap-4">
                <Link className="underline" href={`/precios/${refused.productId}`}>
                  Ver la corrección
                </Link>
                {mayCorrect && (
                  <Link className="underline" href={`/precios/${refused.productId}#correcciones`}>
                    Cambiarla
                  </Link>
                )}
              </p>
              {!mayCorrect && (
                <p className="text-muted-foreground">
                  Cambiar una corrección es de quien maneja el catálogo: el dueño o ventas.
                </p>
              )}
            </>
          )}
        </div>
      )}
    </article>
  )
}
