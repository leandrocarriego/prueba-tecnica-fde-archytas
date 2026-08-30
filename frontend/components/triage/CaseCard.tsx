'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { resolveCase } from '@/app/actions/triage'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useToast } from '@/components/ui/toast'
import { formatMoment, formatPrice } from '@/lib/catalog/format'
import { caseKindLabel, type Case } from '@/lib/triage/types'

interface CaseCardProps {
  item: Case
}

function payloadText(item: Case, key: string): string {
  const value = item.payload[key]
  return typeof value === 'string' || typeof value === 'number' ? String(value) : ''
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
export function CaseCard({ item }: CaseCardProps) {
  const router = useRouter()
  const { addToast } = useToast()
  const [price, setPrice] = useState(payloadText(item, 'price'))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function decide(decision: Record<string, unknown>) {
    setSaving(true)
    setError(null)
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
  }

  return (
    <article className="space-y-3 rounded border p-4">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="text-sm text-muted-foreground">{caseKindLabel(item.kind)}</p>
          <h3 className="font-medium">{item.reason}</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          {formatMoment(item.created_at)}
          {item.occurrences > 1 && ` · se repitió ${item.occurrences} veces`}
        </p>
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

        {item.kind === 'unreadable_history' && (
          <Button disabled={saving} onClick={() => decide({ action: 'ignore' })}>
            Dar el historial por revisado
          </Button>
        )}
      </div>

      {error && <p className="text-sm text-red-700">{error}</p>}
    </article>
  )
}
