import Link from 'next/link'

import { NoPermission } from '@/components/common/NoPermission'
import { InvoiceTable } from '@/components/purchases/InvoiceTable'
import { fetchFromApi } from '@/lib/api/server'
import type { InvoiceList } from '@/lib/purchases/types'

export const metadata = {
  title: 'Facturas — Plataforma Cordillera',
}

interface PageProps {
  searchParams: Promise<{
    q?: string
    payment_state?: string
    with_receipt?: string
    review_state?: string
  }>
}

/**
 * Las facturas de compra, con los filtros de la H4 de 004 y la H1 de 005.
 *
 * Los filtros van en la URL y no en el estado del componente a propósito: una
 * pantalla filtrada se comparte por chat con quien tiene que mirarla, y así
 * llega filtrada.
 */
export default async function InvoicesPage({ searchParams }: PageProps) {
  const filters = await searchParams
  const query = new URLSearchParams({ limit: '200' })
  if (filters.q) query.set('q', filters.q)
  if (filters.payment_state) query.set('payment_state', filters.payment_state)
  if (filters.review_state) query.set('review_state', filters.review_state)
  if (filters.with_receipt) query.set('with_receipt', filters.with_receipt)

  const listing = await fetchFromApi<InvoiceList>(`/invoices?${query.toString()}`)
  if (listing === null) {
    return <NoPermission what="las facturas de compra" />
  }

  const withoutReceipt = listing.items.filter(invoice => !invoice.receipt_issued).length

  return (
    <main className="mx-auto max-w-6xl space-y-8 p-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Facturas</h1>
        <p className="text-sm text-muted-foreground">
          {listing.total} facturas registradas · {withoutReceipt} sin recibo de recepción en esta
          vista.
        </p>
      </header>

      <nav className="flex flex-wrap gap-4 text-sm">
        <Link className="underline" href="/facturas">
          Todas
        </Link>
        <Link className="underline" href="/facturas?payment_state=SIN_PAGOS">
          Sin pagos
        </Link>
        <Link className="underline" href="/facturas?payment_state=PARCIAL">
          Pagadas a medias
        </Link>
        <Link className="underline" href="/facturas?payment_state=SALDADA">
          Saldadas
        </Link>
        <Link className="underline" href="/facturas?with_receipt=false">
          Sin recibo
        </Link>
        <Link className="underline" href="/facturas/revision">
          En revisión
        </Link>
        <Link className="underline" href="/proveedores">
          Proveedores
        </Link>
      </nav>

      <form className="flex flex-wrap items-end gap-2" action="/facturas">
        <label className="text-sm">
          <span className="mb-1 block text-muted-foreground">Buscar por número o proveedor</span>
          <input
            className="rounded border px-3 py-1.5"
            name="q"
            defaultValue={filters.q ?? ''}
            maxLength={255}
          />
        </label>
        <button className="rounded border px-3 py-1.5 text-sm hover:bg-gray-50" type="submit">
          Buscar
        </button>
      </form>

      <InvoiceTable invoices={listing.items} />
    </main>
  )
}
