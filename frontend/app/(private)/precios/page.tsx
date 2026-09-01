import Link from 'next/link'

import { PriceTable } from '@/components/catalog/PriceTable'
import { UpdateNowButton } from '@/components/catalog/UpdateNowButton'
import { UpdateStatus } from '@/components/catalog/UpdateStatus'
import { fetchFromApi } from '@/lib/api/server'
import type { PriceList, PriceUpdateStatus } from '@/lib/catalog/types'
import { ErrorState } from '@/components/ui/state'

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
    <div className="space-y-6">
      <header className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold">Lista de precios</h1>
          <UpdateStatus status={status} />
        </div>
        <UpdateNowButton />
      </header>

      <nav className="flex items-center gap-4 text-sm">
        <Link
          className={highlighted ? 'text-muted-foreground' : 'font-medium text-link'}
          href="/precios"
        >
          Todos
        </Link>
        <Link
          className={highlighted ? 'font-medium text-link' : 'text-muted-foreground'}
          href="/precios?destacados=1"
        >
          Solo los que subieron fuerte
        </Link>
        <Link className="ml-auto text-link hover:underline" href="/revision">
          Revisión
        </Link>
        {/*
          The two parameters of the price update moved to the one parameters
          panel: the signed spec of 003 forbids a parameter living inside the
          screen of the feature that reads it. The link points there, and
          `/precios/configuracion` redirects to the same place.
        */}
        <Link className="text-link hover:underline" href="/configuracion">
          Parámetros
        </Link>
      </nav>

      {prices === null ? (
        <ErrorState title="No pudimos traer los precios.">
          Probá de nuevo en unos minutos.
        </ErrorState>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">{prices.total} productos</p>
          <PriceTable items={prices.items} />
        </>
      )}
    </div>
  )
}
