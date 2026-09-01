import Link from 'next/link'
import { notFound } from 'next/navigation'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { DocumentPreview } from '@/components/purchases/DocumentPreview'
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
import { dueDateTone, invoicePaymentTone, invoiceReviewTone } from '@/lib/ui/tone'

export const metadata = {
  title: 'Factura — Plataforma Cordillera',
}

/**
 * Una factura, con sus pagos, su recibo y lo que dijo su archivo (H2 de 004),
 * con la forma de la guía visual (`3g`).
 *
 * Encabezado con el número y el estado del vencimiento, el original al lado del
 * **estado de pago como una sola barra legible**, y abajo los pagos y el recibo.
 * El recorte del archivo se muestra junto a lo que informó la tabla del portal:
 * es la evidencia sobre la que se decide cuando los dos no coinciden (RF-30).
 *
 * **La tercera tarjeta del diseño, el recibo, no está arriba.** La guía la pone
 * en la fila de arriba junto al original y al estado de pago; acá vive abajo,
 * dentro del panel, porque es donde está el botón que lo emite y su historial.
 * Dibujarla dos veces —resumen arriba, máquina abajo— sería mostrar el mismo
 * estado en dos lugares que pueden dejar de coincidir.
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
      <div className="space-y-4">
        <Link className="text-sm text-link hover:underline" href="/facturas">
          « Volver a las facturas
        </Link>
        <ErrorState title="No pudimos traer esta factura." />
      </div>
    )
  }

  const invoice = read.data
  const warnings = warningsFor(invoice)
  const permissions = session?.permissions ?? {}
  // El estado del vencimiento sale del mapa único de tonos, igual que en la
  // lista y en el calendario: «Venció sin recibo» es la misma píldora roja en
  // las tres pantallas porque ninguna elige su color (`RF-06`).
  const due = dueDateTone({ ...invoice, is_past: false })

  return (
    <div className="space-y-4">
      <header className="space-y-3 rounded-xl border border-border bg-card px-6 py-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <p className="text-xs text-muted-foreground">
              <Link className="hover:text-link hover:underline" href="/facturas">
                Facturas
              </Link>
              {' / '}
              <span className="text-foreground">{invoice.number}</span>
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="amount text-2xl font-semibold tracking-tight text-foreground">
                {invoice.number}
              </h1>
              {due && <Badge tone={due.tone}>{due.label}</Badge>}
              {/*
                Una factura que escribió una persona **no se muestra como algo
                que publicó el portal** (Artículo I): sin esta marca, un total
                tipeado a mano se lee igual que uno leído del origen.
              */}
              {invoice.origin === 'MANUAL' && <Badge tone="info">Cargada a mano</Badge>}
            </div>
            <p className="amount text-[13px] text-muted-ink">
              {invoice.supplier_name ?? (
                <span className="text-warn">{invoice.supplier_text} · sin identificar</span>
              )}
              {' · emitida '}
              <Day value={invoice.issued_on} />
              {invoice.due_on && (
                <>
                  {' · vence '}
                  <Day value={invoice.due_on} />
                </>
              )}
            </p>
          </div>

          {/*
            El original, tal como lo mandó el proveedor (RF-04). Es la acción de
            la pantalla que no cambia nada, así que va en contorno: el naranja de
            esta pantalla se gasta en emitir el recibo, abajo (`UI-05`).
          */}
          <a
            className="inline-flex h-10 items-center rounded-md border border-input bg-card px-4 text-sm font-semibold text-foreground hover:bg-muted"
            href={`/api/proxy/invoices/${invoice.id}/file`}
            rel="noreferrer"
            target="_blank"
          >
            Ver original
          </a>
        </div>

        {/* Lo que anda mal, arriba de los números que califica (`RF-14`). */}
        {warnings.map(warning => (
          <Notice key={warning} tone="warn" title={warning} />
        ))}
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        {/*
          El estado de pago como **una sola barra**, que es lo que la guía pide:
          cuánto se pagó de cuánto, y el resto dicho como número y no como una
          resta que tenga que hacer quien mira.
        */}
        <section className="space-y-3 rounded-xl border border-border bg-card p-5">
          <h2 className="section-label">Estado de pago</h2>
          <p className="flex flex-wrap items-baseline gap-2">
            <Money value={invoice.paid} as="span" className="text-2xl font-medium" />
            <span className="text-sm text-muted-foreground">
              de <Money value={invoice.total} as="span" />
            </span>
          </p>
          <div
            aria-hidden
            className="h-2.5 overflow-hidden rounded-full bg-muted"
            /* Una proporción, no un color: la paleta no la gobierna. */
          >
            <div
              className="h-full rounded-full bg-info"
              style={{ width: `${Math.min(Math.max(invoice.paid_pct, 0), 100)}%` }}
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={invoicePaymentTone(invoice.payment_state)}>
              {paymentStateLabel(invoice.payment_state)}
              {invoice.payment_state === 'PARCIAL' && ` ${invoice.paid_pct} %`}
            </Badge>
            {Number(invoice.balance) > 0 && (
              <Badge tone="warn">
                Resto <Money value={invoice.balance} as="span" />
              </Badge>
            )}
            {/*
              Cuando lo que informa el portal y lo que sale de los pagos
              imputados no coinciden, la factura lo dice: no gana ninguno
              (RF-45, RF-46 de 005).
            */}
            {invoice.payment_state_disagrees && (
              <Badge tone="danger">El portal informa otro estado</Badge>
            )}
          </div>
        </section>

        {/*
          El original, **mostrado** y no sólo enlazado, que es lo que la guía
          dibuja en `3g`. Lo que se decide en esta pantalla es si el número de la
          tabla y el del papel son el mismo, y hasta acá eso obligaba a abrir el
          archivo en otra pestaña, mirarlo, volver y acordarse: comparar dos
          cosas que no están a la vista al mismo tiempo es comparar de memoria.
        */}
        <section className="space-y-3 rounded-xl border border-border bg-card p-5">
          <h2 className="section-label">Documento original</h2>
          <DocumentPreview invoiceId={invoice.id} document={invoice.document} />
        </section>
      </div>

      {/*
        Qué se decidió, quién y cuándo (RF-32). Se guardaba en la base desde el
        primer día y no salía en la respuesta, así que ninguna pantalla podía
        decirlo — que es lo que el criterio firmado pide leer.
      */}
      <p className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
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
