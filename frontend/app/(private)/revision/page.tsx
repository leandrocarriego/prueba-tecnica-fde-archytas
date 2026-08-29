import Link from 'next/link'

import { CaseCard } from '@/components/triage/CaseCard'
import { RuleList } from '@/components/triage/RuleList'
import { fetchFromApi } from '@/lib/api/server'
import type { CaseList, Rule } from '@/lib/triage/types'

export const metadata = {
  title: 'Revisión — Plataforma Cordillera',
}

/**
 * What the update set aside, and the decisions taken about it (H7 and H8).
 *
 * This screen is the visible half of Artículo II: nothing is discarded, so
 * everything the pipeline could not resolve on its own ends up here with the
 * reason it could not — and what a person decides is kept, so the queue empties
 * instead of growing.
 */
export default async function ReviewPage() {
  const [cases, rules] = await Promise.all([
    fetchFromApi<CaseList>('/triage/cases?limit=100'),
    fetchFromApi<Rule[]>('/triage/rules'),
  ])

  if (cases === null) {
    return (
      <main className="mx-auto max-w-4xl space-y-4 p-8">
        <h1 className="text-2xl font-bold">Revisión</h1>
        <p className="rounded border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          Esta pantalla es de compras y del dueño. Si necesitás resolver un caso, pedíselo a quien
          maneja compras.
        </p>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <Link className="text-sm text-muted-foreground underline" href="/precios">
        « Volver a la lista de precios
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Revisión</h1>
        <p className="text-sm text-muted-foreground">
          {cases.total === 0
            ? 'No quedó nada sin resolver en la última actualización.'
            : `${cases.total} ${cases.total === 1 ? 'caso pendiente' : 'casos pendientes'}.`}
        </p>
      </header>

      <section className="space-y-3">
        {cases.items.length === 0 ? (
          <p className="rounded border border-dashed p-8 text-center text-muted-foreground">
            Nada apartado. Cuando el sistema no pueda resolver algo solo, va a aparecer acá con el
            motivo.
          </p>
        ) : (
          cases.items.map(item => <CaseCard key={item.id} item={item} />)
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Decisiones guardadas</h2>
        <p className="text-sm text-muted-foreground">
          El sistema las aplica solo a los casos iguales. Si dejás una sin efecto, esos casos
          vuelven a esta pantalla.
        </p>
        <RuleList rules={rules ?? []} />
      </section>
    </main>
  )
}
