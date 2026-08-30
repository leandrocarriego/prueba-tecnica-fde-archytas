import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { InvoicePanel } from '@/components/purchases/InvoicePanel'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import { day, money } from '@/lib/format'
import { paymentStateLabel, reviewStateLabel, warningFor } from '@/lib/purchases/labels'
import type { Invoice, Payment, Receipt } from '@/lib/purchases/types'

export const metadata = {
  title: 'Factura — Plataforma Cordillera',
}

/**
 * Una factura, con sus pagos, su recibo y lo que dijo su archivo (H2 de 004).
 *
 * El recorte del archivo se muestra junto a lo que informó la tabla del portal:
 * es la evidencia sobre la que se decide cuando los dos no coinciden (RF-30).
 */
export default async function InvoicePage({ params }: { params: Promise<{ invoiceId: string }> }) {
  const { invoiceId } = await params
  const [invoice, payments, receipt, session] = await Promise.all([
    fetchFromApi<Invoice>(`/invoices/${invoiceId}`),
    fetchFromApi<Payment[]>(`/invoices/${invoiceId}/payments`),
    fetchFromApi<Receipt>(`/invoices/${invoiceId}/receipt`),
    getSession(),
  ])

  if (invoice === null) {
    return <NoPermission what="las facturas de compra" />
  }

  const warning = warningFor(invoice)
  const permissions = session?.permissions ?? {}

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <Link className="text-sm text-muted-foreground underline" href="/facturas">
        « Volver a las facturas
      </Link>

      <header className="space-y-2">
        <h1 className="text-2xl font-bold">Factura {invoice.number}</h1>
        <p className="text-sm text-muted-foreground">
          {invoice.supplier_name ?? `${invoice.supplier_text} (sin identificar)`} ·{' '}
          {day(invoice.issued_on)} · vence {day(invoice.due_on)}
        </p>
        {warning && (
          <p className="rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
            {warning}
          </p>
        )}
      </header>

      <dl className="grid gap-4 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-muted-foreground">Monto</dt>
          <dd className="text-lg font-medium">{money(invoice.total)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Pagado</dt>
          <dd className="text-lg font-medium">{money(invoice.paid)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Saldo</dt>
          <dd className="text-lg font-medium">{money(invoice.balance)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Estado</dt>
          <dd className="text-lg font-medium">{paymentStateLabel(invoice.payment_state)}</dd>
        </div>
      </dl>

      {invoice.document && (
        <section className="space-y-2">
          <h2 className="text-lg font-medium">Lo que dice el archivo</h2>
          <p className="text-sm text-muted-foreground">
            {invoice.document.agrees
              ? 'Coincide con lo que informa el portal.'
              : (invoice.document.reason ?? 'No coincide con lo que informa el portal.')}
          </p>
          <pre className="max-h-72 overflow-auto rounded bg-gray-50 p-3 text-xs">
            {invoice.document.excerpt || 'Sin contenido legible.'}
          </pre>
        </section>
      )}

      <p className="text-sm text-muted-foreground">
        Revisión: {reviewStateLabel(invoice.review_state)}
        {invoice.arrival_count > 1 && ` · llegó ${invoice.arrival_count} veces`}
      </p>

      <InvoicePanel
        invoice={invoice}
        payments={payments ?? []}
        receipt={receipt}
        canPay={canEdit(permissions, 'PAYMENTS')}
        canIssue={canEdit(permissions, 'RECEIPTS')}
      />
    </main>
  )
}
