import Link from 'next/link'

import { PriceTable } from '@/components/catalog/PriceTable'
import { UpdateNowButton } from '@/components/catalog/UpdateNowButton'
import { UpdateStatus } from '@/components/catalog/UpdateStatus'
import { fetchFromApi } from '@/lib/api/server'
import type { PriceList, PriceUpdateStatus } from '@/lib/catalog/types'

/** The supplier publishes a hundred products; the page shows them all. */
const PAGE_SIZE = 200

export const metadata = {
  title: 'Precios — Plataforma Cordillera',
}

/**
 * The prices screen (RF-04), with the state of the update on top (RF-09, RF-11)
 * and the button that brings the list without waiting (RF-14).
 *
 * A Server Component: it holds the session cookie already, so it asks the API
 * itself and ships rendered HTML instead of making the browser do a round trip
 * through the proxy.
 */
export default async function PricesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; destacados?: string }>
}) {
  const { q, destacados } = await searchParams
  const highlighted = destacados === '1'

  const query = new URLSearchParams({ limit: String(PAGE_SIZE) })
  if (q) query.set('q', q)
  if (highlighted) query.set('highlighted', 'true')

  const [prices, status] = await Promise.all([
    fetchFromApi<PriceList>(`/prices?${query.toString()}`),
    fetchFromApi<PriceUpdateStatus>('/price-updates/status'),
  ])

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-8">
      <header className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold">Lista de precios</h1>
          <UpdateStatus status={status} />
        </div>
        <UpdateNowButton />
      </header>

      <nav className="flex items-center gap-4 text-sm">
        <Link
          className={highlighted ? 'text-muted-foreground' : 'font-medium underline'}
          href="/precios"
        >
          Todos
        </Link>
        <Link
          className={highlighted ? 'font-medium underline' : 'text-muted-foreground'}
          href="/precios?destacados=1"
        >
          Solo los que subieron fuerte
        </Link>
        <Link className="ml-auto text-muted-foreground underline" href="/revision">
          Revisión
        </Link>
        <Link className="text-muted-foreground underline" href="/precios/configuracion">
          Configuración
        </Link>
      </nav>

      {prices === null ? (
        <p className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-900">
          No pudimos traer los precios. Probá de nuevo en unos minutos.
        </p>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">{prices.total} productos</p>
          <PriceTable items={prices.items} />
        </>
      )}
    </main>
  )
}
