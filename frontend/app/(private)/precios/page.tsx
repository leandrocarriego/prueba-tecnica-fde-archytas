import { PriceFilters } from '@/components/catalog/PriceFilters'
import { PriceHeader } from '@/components/catalog/PriceHeader'
import { PriceSummaryCards } from '@/components/catalog/PriceSummaryCards'
import { PriceTable } from '@/components/catalog/PriceTable'
import { fetchFromApi } from '@/lib/api/server'
import type { CategoryList, PriceList, PriceSummary, PriceUpdateStatus } from '@/lib/catalog/types'
import { ErrorState } from '@/components/ui/state'
import { Notice } from '@/components/ui/notice'

/** The supplier publishes a hundred products; the page shows them all. */
const PAGE_SIZE = 200

export const metadata = {
  title: 'Precios — Plataforma Cordillera',
}

interface PricesSearchParams {
  q?: string
  rubro?: string
  changed?: string
}

/** A positive integer from the address bar, or null when it is not one. */
function categoryFrom(value: string | undefined): number | null {
  const parsed = Number.parseInt(value ?? '', 10)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

/**
 * La pantalla de precios (RF-04), con la forma de la guía visual (`3k`).
 *
 * Un encabezado que muestra la sincronización como un hecho (RF-09, RF-11), las
 * cuatro cuentas de todo el catálogo, la tabla filtrable con el rubro por fila,
 * y abajo la revisión de rubros y sus formas escritas.
 *
 * Un Server Component: ya tiene la cookie de sesión, así que le pregunta a la
 * API él mismo y manda HTML renderizado en vez de un ida y vuelta del navegador.
 */
export default async function PricesPage({
  searchParams,
}: {
  searchParams: Promise<PricesSearchParams>
}) {
  const { q, rubro, changed } = await searchParams
  const categoryId = categoryFrom(rubro)
  const onlyChanged = changed === '1'

  const query = new URLSearchParams({ limit: String(PAGE_SIZE) })
  if (q) query.set('q', q)
  if (categoryId !== null) query.set('category_id', String(categoryId))
  if (onlyChanged) query.set('changed', 'true')

  const [prices, summary, status, categories] = await Promise.all([
    fetchFromApi<PriceList>(`/prices?${query.toString()}`),
    fetchFromApi<PriceSummary>('/prices/summary'),
    fetchFromApi<PriceUpdateStatus>('/price-updates/status'),
    fetchFromApi<CategoryList>('/categories'),
  ])

  return (
    <div className="space-y-4">
      <PriceHeader total={prices?.total ?? 0} status={status} />

      {status?.is_stalled && (
        // El aviso rojo sigue gritando cuando la extracción dejó de funcionar:
        // la píldora del encabezado dice «Atrasado», y esto explica cuánto y
        // desde cuándo (RF-11). Los precios de abajo pueden estar viejos.
        <Notice tone="danger" title="La actualización de precios dejó de funcionar.">
          Van {status.consecutive_failures} consultas seguidas sin éxito. Los precios de abajo
          pueden estar desactualizados.
        </Notice>
      )}

      {summary && <PriceSummaryCards summary={summary} />}

      {prices === null ? (
        <ErrorState title="No pudimos traer los precios.">
          Probá de nuevo en unos minutos.
        </ErrorState>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-card">
          <PriceFilters
            categories={(categories?.items ?? []).map(({ id, name }) => ({ id, name }))}
            q={q ?? ''}
            changed={onlyChanged}
            categoryId={categoryId}
          />
          <PriceTable items={prices.items} />
        </div>
      )}
    </div>
  )
}
