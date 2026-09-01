import Link from 'next/link'
import { notFound } from 'next/navigation'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { InvoicePanel } from '@/components/purchases/InvoicePanel'
import { Day, Money } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Notice } from '@/components/ui/notice'
import { ErrorState } from '@/components/ui/state'
import { readFromApi } from '@/lib/api/server'
import { formatMoment } from '@/lib/catalog/format'
import { canEdit } from '@/lib/auth/permissions'
import { paymentStateLabel, reviewStateLabel, warningsFor } from '@/lib/purchases/labels'
import type { Invoice, Payment, Receipt } from '@/lib/purchases/types'
import { invoicePaymentTone, invoiceReviewTone } from '@/lib/ui/tone'

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
  const [read, payments, receipt, session] = await Promise.all([
    readFromApi<Invoice>(`/invoices/${invoiceId}`),
    readFromApi<Payment[]>(`/invoices/${invoiceId}/payments`),
    readFromApi<Receipt>(`/invoices/${invoiceId}/receipt`),
    getSession(),
  ])

  // Tres respuestas y tres frases. Una factura que no está no es una factura
  // que no es tuya, y ninguna de las dos es la API sin contestar.
  if (!read.ok) {
    if (read.failure === 'unauthorized') {
      return <NoPermission what="las facturas de compra" />
    }
    if (read.failure === 'missing') notFound()
    return (
      <div className="space-y-6">
        <Link className="text-sm text-link hover:underline" href="/facturas">
          « Volver a las facturas
        </Link>
        <ErrorState title="No pudimos traer esta factura" />
      </div>
    )
  }

  const invoice = read.data

  const warnings = warningsFor(invoice)
  const permissions = session?.permissions ?? {}

  return (
    <div className="space-y-8">
      <Link className="text-sm text-link hover:underline" href="/facturas">
        « Volver a las facturas
      </Link>

      <header className="space-y-2">
        <h1 className="text-2xl font-bold">Factura {invoice.number}</h1>
        <p className="text-sm text-muted-foreground">
          {invoice.supplier_name ?? `${invoice.supplier_text} (sin identificar)`} ·{' '}
          <Day value={invoice.issued_on} /> · vence <Day value={invoice.due_on} />
        </p>
        {/* Lo que anda mal, arriba de los números que califica (`RF-14`). */}
        {warnings.map(warning => (
          <Notice key={warning} tone="warn" title={warning} />
        ))}
      </header>

      <dl className="grid gap-4 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-muted-foreground">Monto</dt>
          <Money value={invoice.total} as="dd" className="text-lg font-medium" />
        </div>
        <div>
          <dt className="text-muted-foreground">Pagado</dt>
          <Money value={invoice.paid} as="dd" className="text-lg font-medium" />
        </div>
        <div>
          <dt className="text-muted-foreground">Saldo</dt>
          <Money value={invoice.balance} as="dd" className="text-lg font-medium" />
        </div>
        <div>
          <dt className="text-muted-foreground">Estado</dt>
          <dd className="mt-1">
            <Badge tone={invoicePaymentTone(invoice.payment_state)}>
              {paymentStateLabel(invoice.payment_state)}
            </Badge>
          </dd>
        </div>
      </dl>

      {invoice.document && (
        <section className="space-y-2">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-medium">Lo que dice el archivo</h2>
            {/*
              El original, tal como lo mandó el proveedor (RF-04). Va acá y no
              en la lista porque es la pregunta que se hace parado sobre una
              factura: «¿de dónde salió este número?». Se abre en otra pestaña
              para no perder la factura que se estaba mirando.
            */}
            <a
              className="text-sm text-link hover:underline"
              href={`/api/proxy/invoices/${invoice.id}/file`}
              rel="noreferrer"
              target="_blank"
            >
              Abrir el archivo original
            </a>
          </div>
          <p className="text-sm text-muted-foreground">
            {invoice.document.agrees
              ? 'Coincide con lo que informa el portal.'
              : (invoice.document.reason ?? 'No coincide con lo que informa el portal.')}
            {invoice.document.read_supplier_tax_id &&
              ` El archivo trae el CUIT ${invoice.document.read_supplier_tax_id}.`}
          </p>
          <pre className="max-h-72 overflow-auto rounded bg-muted p-3 text-xs">
            {invoice.document.excerpt || 'Sin contenido legible.'}
          </pre>
        </section>
      )}

      {/*
        Qué se decidió, quién y cuándo (RF-32). Se guardaba en la base desde el
        primer día y no salía en la respuesta, así que ninguna pantalla podía
        decirlo — que es lo que el criterio firmado pide leer.
      */}
      <p className="flex flex-wrap items-center gap-1.5 text-sm text-muted-foreground">
        Revisión:{' '}
        <Badge tone={invoiceReviewTone(invoice.review_state)}>
          {reviewStateLabel(invoice.review_state)}
        </Badge>
        {invoice.resolved_at &&
          ` · la resolvió ${invoice.resolved_by_name ?? 'alguien que ya no tiene cuenta'} el ${formatMoment(invoice.resolved_at)}`}
        {invoice.arrival_count > 1 && ` · llegó ${invoice.arrival_count} veces`}
      </p>

      <InvoicePanel
        invoice={invoice}
        payments={payments.ok ? payments.data : []}
        receipt={receipt.ok ? receipt.data : null}
        canPay={canEdit(permissions, 'PAYMENTS')}
        canIssue={canEdit(permissions, 'RECEIPTS')}
      />
    </div>
  )
}
