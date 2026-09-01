import Link from 'next/link'

import { NoPermission } from '@/components/common/NoPermission'
import { ErrorState } from '@/components/ui/state'
import { InvoiceFilters } from '@/components/purchases/InvoiceFilters'
import { InvoiceTable } from '@/components/purchases/InvoiceTable'
import { readFromApi } from '@/lib/api/server'
import type { InvoiceList, SupplierList } from '@/lib/purchases/types'

export const metadata = {
  title: 'Facturas — Plataforma Cordillera',
}

interface PageProps {
  searchParams: Promise<{
    q?: string
    supplier_id?: string
    issued_from?: string
    issued_to?: string
    order?: string
    payment_state?: string
    with_receipt?: string
    review_state?: string
  }>
}

/**
 * Las facturas de compra, con los filtros de la H8 de 004 y la H1 de 005.
 *
 * Los filtros van en la URL y no en el estado del componente a propósito: una
 * pantalla filtrada se comparte por chat con quien tiene que mirarla, y así
 * llega filtrada.
 *
 * Lo que la búsqueda alcanza lo decide el backend y no esta pantalla: el número,
 * el nombre tal como llegó escrito y —para una factura ya asignada— el CUIT y la
 * razón social del padrón (RF-41, RF-42). Acá sólo se arma la URL.
 */
export default async function InvoicesPage({ searchParams }: PageProps) {
  const filters = await searchParams
  const query = new URLSearchParams({ limit: '200' })
  for (const name of [
    'q',
    'supplier_id',
    'issued_from',
    'issued_to',
    'order',
    'payment_state',
    'review_state',
    'with_receipt',
  ] as const) {
    const value = filters[name]
    if (value) query.set(name, value)
  }

  // El tercer pedido existe sólo por su `total`: cuántas facturas están sin
  // recibo es una pregunta sobre el sistema, no sobre la página que se está
  // mirando (RF-32). Contando `items` decía «46 sin recibo» cuando el límite
  // de 200 recortaba la lista, y encima cambiaba al filtrar por otra cosa.
  const [read, suppliers, missing] = await Promise.all([
    readFromApi<InvoiceList>(`/invoices?${query.toString()}`),
    readFromApi<SupplierList>('/suppliers'),
    readFromApi<InvoiceList>('/invoices?with_receipt=false&limit=1'),
  ])

  // Un 403 y una caída del backend son dos frases distintas. Decirle «no tenés
  // permiso» al dueño porque la API no contestó lo manda a pedirse a sí mismo
  // un permiso que ya tiene, y a no mirar el problema que sí hay.
  if (!read.ok) {
    if (read.failure === 'unauthorized') {
      return <NoPermission what="las facturas de compra" />
    }
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Facturas</h1>
        <ErrorState title="No pudimos traer las facturas" />
      </div>
    )
  }

  const listing = read.data
  const withoutReceipt = missing.ok ? missing.data.total : null

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Facturas</h1>
        <p className="text-sm text-muted-foreground">
          {listing.total} facturas registradas
          {withoutReceipt !== null && ` · ${withoutReceipt} sin recibo de recepción`}.
        </p>
      </header>

      <nav className="flex flex-wrap gap-4 text-sm">
        <Link className="text-link hover:underline" href="/facturas">
          Todas
        </Link>
        <Link className="text-link hover:underline" href="/facturas?payment_state=SIN_PAGOS">
          Sin pagos
        </Link>
        <Link className="text-link hover:underline" href="/facturas?payment_state=PARCIAL">
          Pagadas a medias
        </Link>
        <Link className="text-link hover:underline" href="/facturas?payment_state=SALDADA">
          Saldadas
        </Link>
        <Link className="text-link hover:underline" href="/facturas?with_receipt=false">
          Sin recibo
        </Link>
        <Link className="text-link hover:underline" href="/facturas/revision">
          En revisión
        </Link>
        <Link className="text-link hover:underline" href="/facturas/pagos">
          Comprobantes por repartir
        </Link>
        <Link className="text-link hover:underline" href="/facturas/incidentes">
          Incidentes de recibo
        </Link>
        <Link className="text-link hover:underline" href="/proveedores">
          Proveedores
        </Link>
      </nav>

      <InvoiceFilters suppliers={suppliers.ok ? suppliers.data.items : []} values={filters} />

      <InvoiceTable invoices={listing.items} />
    </div>
  )
}
