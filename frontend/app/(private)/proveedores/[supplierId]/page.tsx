import Link from 'next/link'

import { NoPermission } from '@/components/common/NoPermission'
import { InvoiceTable } from '@/components/purchases/InvoiceTable'
import { fetchFromApi } from '@/lib/api/server'
import { count, decimal, money } from '@/lib/format'
import type { InvoiceList, Supplier, SupplierTotals } from '@/lib/purchases/types'

export const metadata = {
  title: 'Proveedor — Plataforma Cordillera',
}

const MISSING_LABELS: Record<string, string> = {
  tax_id: 'CUIT',
  email: 'correo',
  phone: 'teléfono',
  payment_term_days: 'plazo de pago',
}

/**
 * Un proveedor: su ficha, sus facturas y cuánto se le debe (H3 y H5 de 004).
 *
 * Debajo de cada total va **cuántas facturas quedaron afuera** — las que están
 * en revisión y las señaladas como inconsistentes— porque un total que descarta
 * filas en silencio es un total que el cliente va a desmentir la primera vez
 * que lo verifique a mano (RF-23 de 004, RF-28 de 005).
 */
export default async function SupplierPage({
  params,
}: {
  params: Promise<{ supplierId: string }>
}) {
  const { supplierId } = await params
  const [supplier, totals, invoices] = await Promise.all([
    fetchFromApi<Supplier>(`/suppliers/${supplierId}`),
    fetchFromApi<SupplierTotals>(`/suppliers/${supplierId}/totals`),
    fetchFromApi<InvoiceList>(`/suppliers/${supplierId}/invoices?limit=200`),
  ])

  if (supplier === null) {
    return <NoPermission what="el padrón de proveedores" />
  }

  return (
    <main className="mx-auto max-w-5xl space-y-8 p-8">
      <Link className="text-sm text-muted-foreground underline" href="/proveedores">
        « Volver al padrón
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">{supplier.legal_name}</h1>
        <p className="text-sm text-muted-foreground">
          {supplier.tax_id ?? 'CUIT: falta'} ·{' '}
          {supplier.payment_term_days === null
            ? 'plazo: falta'
            : `plazo pactado: ${supplier.payment_term_days} días`}
        </p>
        {(supplier.missing ?? []).length > 0 && (
          <p className="text-sm text-amber-800">
            El portal no publicó:{' '}
            {(supplier.missing ?? []).map(field => MISSING_LABELS[field] ?? field).join(', ')}.
          </p>
        )}
      </header>

      {totals && (
        <section className="space-y-4">
          <dl className="grid gap-4 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-muted-foreground">Facturado</dt>
              <dd className="text-lg font-medium">{money(totals.invoiced)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Pagado</dt>
              <dd className="text-lg font-medium">{money(totals.paid)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Se le debe</dt>
              <dd className="text-lg font-medium">{money(totals.owed)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Atraso promedio</dt>
              <dd className="text-lg font-medium">
                {totals.average_delay_days === null
                  ? 'sin atrasos'
                  : `${decimal(totals.average_delay_days)} días`}
              </dd>
            </div>
          </dl>

          <p className="text-sm text-muted-foreground">
            {count(totals.invoices)} facturas entran en estos números.{' '}
            {totals.excluded === 0
              ? 'No quedó ninguna afuera.'
              : `${totals.excluded} quedaron afuera por estar en revisión o señaladas como inconsistentes.`}
          </p>

          <div>
            <h2 className="mb-2 text-lg font-medium">Deuda por antigüedad</h2>
            <table className="w-full max-w-xl text-sm">
              <tbody>
                {totals.aging.map(bucket => (
                  <tr key={bucket.label} className="border-b">
                    <td className="py-2">{bucket.label}</td>
                    <td className="py-2 text-right">{money(bucket.amount)}</td>
                    <td className="py-2 text-right text-muted-foreground">
                      {count(bucket.invoices)} facturas
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Sus facturas</h2>
        <InvoiceTable invoices={invoices?.items ?? []} />
      </section>
    </main>
  )
}
