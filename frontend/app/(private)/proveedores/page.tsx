import Link from 'next/link'

import { NoPermission } from '@/components/common/NoPermission'
import { Code, Money } from '@/components/ui/amount'
import { ErrorState } from '@/components/ui/state'
import { readFromApi } from '@/lib/api/server'
import { count } from '@/lib/format'
import type { SupplierList } from '@/lib/purchases/types'

export const metadata = {
  title: 'Proveedores — Plataforma Cordillera',
}

const MISSING_LABELS: Record<string, string> = {
  tax_id: 'CUIT',
  email: 'correo',
  phone: 'teléfono',
  payment_term_days: 'plazo de pago',
}

/**
 * El padrón de proveedores, como lo publica el portal (H2 de 004).
 *
 * Lo que el portal no publicó se dice **falta**, no se deja en blanco: una
 * celda vacía se lee igual que un dato que nadie se molestó en leer, y no son
 * lo mismo (RF-15, RF-20).
 */
export default async function SuppliersPage() {
  const read = await readFromApi<SupplierList>('/suppliers')
  if (!read.ok) {
    if (read.failure === 'unauthorized') {
      return <NoPermission what="el padrón de proveedores" />
    }
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Proveedores</h1>
        <ErrorState title="No pudimos traer el padrón" />
      </div>
    )
  }

  const listing = read.data

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Proveedores</h1>
        <p className="text-sm text-muted-foreground">
          {listing.total} proveedores en el padrón. El padrón sale del portal: el sistema no da de
          alta ninguno por su cuenta.
        </p>
      </header>

      <nav className="flex gap-4 text-sm">
        <Link className="text-link hover:underline" href="/proveedores/grafias">
          Grafías guardadas
        </Link>
        <Link className="text-link hover:underline" href="/facturas">
          Facturas
        </Link>
      </nav>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b text-left text-muted-foreground">
            <tr>
              <th className="py-2">Proveedor</th>
              <th className="py-2">CUIT</th>
              <th className="py-2">Plazo</th>
              <th className="py-2 text-right">Saldo</th>
              <th className="py-2 text-right">Facturas</th>
              <th className="py-2">Falta</th>
            </tr>
          </thead>
          <tbody>
            {listing.items.map(supplier => (
              <tr key={supplier.id} className="border-b align-top">
                <td className="py-2">
                  <Link className="text-link hover:underline" href={`/proveedores/${supplier.id}`}>
                    {supplier.legal_name}
                  </Link>
                </td>
                <Code value={supplier.tax_id} cell className="py-2 text-left" />
                <td className="py-2">
                  {supplier.payment_term_days === null ? '—' : `${supplier.payment_term_days} días`}
                </td>
                <Money value={supplier.balance} cell className="py-2" />
                <td className="amount py-2 text-right">{count(supplier.invoice_count)}</td>
                <td className="py-2 text-warn">
                  {(supplier.missing ?? [])
                    .map(field => MISSING_LABELS[field] ?? field)
                    .join(', ') || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
