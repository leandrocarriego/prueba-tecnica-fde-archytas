import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { CaseCard } from '@/components/triage/CaseCard'
import { RuleList } from '@/components/triage/RuleList'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import { formatMoment } from '@/lib/catalog/format'
import type { CategoryList } from '@/lib/catalog/types'
import { sectionLabel, type CaseList, type Rule } from '@/lib/triage/types'

export const metadata = {
  title: 'Revisión — Plataforma Cordillera',
}

interface ReviewPageProps {
  searchParams: Promise<{ area?: string }>
}

/**
 * What the platform set aside, and the decisions taken about it.
 *
 * This screen is the visible half of Artículo II: nothing is discarded, so
 * everything the pipeline could not resolve on its own ends up here with the
 * reason it could not — and what a person decides is kept, so the queue empties
 * instead of growing.
 *
 * Desde la 011 es **la** lista, y no la de precios. Cuatro orígenes más —el
 * padrón, los comprobantes, el buzón y las ventas— apartaban en silencio, y
 * ahora caen acá. Que sea una sola no es una comodidad: lo que hizo que nadie
 * mirara el buzón del portal no fue que fuera largo, fue que era otro lugar más
 * al que había que acordarse de entrar.
 *
 * **Y cada uno ve lo suyo** (RF-12). El recorte lo hace el backend contra las
 * áreas que el rol de quien mira alcanza; acá no hay una segunda copia de esa
 * regla, ni la puede haber: la pantalla dibuja lo que le llega.
 */
export default async function ReviewPage({ searchParams }: ReviewPageProps) {
  const { area } = await searchParams
  const session = await getSession()

  /*
    Las reglas aprendidas son **de precios**, y sólo las pide quien alcanza esa
    sección. Antes esta página las pedía siempre, y con la ruta de los casos
    abierta eso pasa a ser un 403 para cualquiera que no llegue a `PRICES` — un
    403 que `rules ?? []` disfrazaría de lista vacía. Un error amortiguado por
    accidente no es un comportamiento: es uno que nadie testea. Ahora la
    pregunta no se hace, y el bloque no se dibuja.
  */
  const mayReadRules = session !== null && canEdit(session.permissions, 'PRICES')
  const query = area ? `&section=${encodeURIComponent(area)}` : ''

  const [cases, rules, categories] = await Promise.all([
    fetchFromApi<CaseList>(`/triage/cases?limit=100${query}`),
    mayReadRules ? fetchFromApi<Rule[]>('/triage/rules') : Promise.resolve(null),
    // Los rubros, para que un caso de forma escrita nueva se pueda resolver acá
    // mismo (RF-14 de 010). Los pide la pantalla y no la tarjeta: `CaseCard` es
    // de `triage` y no tiene por qué saber que existe un catálogo.
    fetchFromApi<CategoryList>('/categories'),
  ])
  // Asked here so a card can offer the second door when a load is refused by a
  // correction in force. It is not the permission that opens this screen —
  // cualquier sesión llega, y el backend recorta por área— sino la de cambiar
  // una corrección, que es `PRODUCT_CATALOG` en escritura. Esto sólo mantiene
  // fuera de la tarjeta un link que respondería 403.
  const mayCorrect = session !== null && canEdit(session.permissions, 'PRODUCT_CATALOG')

  if (cases === null) {
    return (
      <main className="mx-auto max-w-4xl space-y-4 p-8">
        <h1 className="text-2xl font-bold">Revisión</h1>
        <p className="rounded border border-warn-border bg-warn-surface p-4 text-sm text-warn">
          No pudimos traer los pendientes. Probá de nuevo en un momento.
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
        <h1 className="text-2xl font-bold">Revisar esto</h1>
        <p className="text-sm text-muted-foreground">
          {cases.pending_total === 0
            ? 'No quedó nada sin resolver.'
            : `${cases.pending_total} ${
                cases.pending_total === 1 ? 'pendiente' : 'pendientes'
              } sin resolver.`}
          {/*
            El más viejo, que es lo que deja ver si la lista se está abandonando
            antes de que sea un problema (RF-16).
          */}
          {cases.oldest_at !== null &&
            ` El más viejo espera desde ${formatMoment(cases.oldest_at)}.`}
        </p>
      </header>

      {/*
        El filtro por área (RF-22). Las opciones las manda el backend con la
        página: qué áreas alcanza un rol lo contesta `identity` y nadie más, y
        una copia de esa matriz acá sería la misma regla en dos lugares. Con una
        sola área no se dibuja, porque no hay nada que elegir — que es el caso de
        Marcela y el de Julián, y deja el filtro donde sirve: en la pantalla del
        dueño, que es quien ve todo.
      */}
      {cases.sections.length > 1 && (
        <nav className="flex flex-wrap gap-2 text-sm">
          <Link
            className={`rounded border px-3 py-1 ${!area ? 'bg-muted font-medium' : ''}`}
            href="/revision"
          >
            Todo
          </Link>
          {cases.sections.map(section => (
            <Link
              key={section}
              className={`rounded border px-3 py-1 ${
                area === section ? 'bg-muted font-medium' : ''
              }`}
              href={`/revision?area=${section}`}
            >
              {sectionLabel(section)}
            </Link>
          ))}
        </nav>
      )}

      <section className="space-y-3">
        {cases.items.length === 0 ? (
          <p className="rounded border border-dashed p-8 text-center text-muted-foreground">
            Nada apartado. Cuando el sistema no pueda resolver algo solo, va a aparecer acá con el
            motivo.
          </p>
        ) : (
          cases.items.map(item => (
            <CaseCard
              key={item.id}
              item={item}
              mayCorrect={mayCorrect}
              categories={categories?.items ?? []}
            />
          ))
        )}
      </section>

      {mayReadRules && (
        <section className="space-y-3">
          <h2 className="text-lg font-medium">Decisiones guardadas</h2>
          <p className="text-sm text-muted-foreground">
            El sistema las aplica solo a los casos iguales. Si dejás una sin efecto, esos casos
            vuelven a esta pantalla.
          </p>
          <RuleList rules={rules ?? []} />
        </section>
      )}
    </main>
  )
}
