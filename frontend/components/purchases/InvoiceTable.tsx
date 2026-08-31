import Link from 'next/link'

import { day, money } from '@/lib/format'
import { fileKindLabel, isScanned, paymentStateLabel, warningsFor } from '@/lib/purchases/labels'
import type { Invoice } from '@/lib/purchases/types'

/**
 * La lista de facturas, con lo que cada una necesita que se vea de un vistazo.
 *
 * El estado de pago que muestra es el que sale de los pagos imputados, nunca el
 * que informa el portal (RF-45 de 005). Cuando los dos no coinciden, la fila lo
 * dice: no gana ninguno.
 *
 * La columna **Formato** es RF-05, y está acá y no en la ficha porque el
 * criterio firmado pide distinguir a simple vista cuáles llegaron escaneadas —
 * 46 de cada 100— y eso sólo se ve mirando la lista entera. Las escaneadas van
 * marcadas: son las que el lector acierta menos.
 */
export function InvoiceTable({ invoices }: { invoices: Invoice[] }) {
  if (invoices.length === 0) {
    return (
      <p className="rounded border border-dashed p-8 text-center text-muted-foreground">
        No hay facturas que coincidan con lo que buscás.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b text-left text-muted-foreground">
          <tr>
            <th className="py-2">Factura</th>
            <th className="py-2">Proveedor</th>
            <th className="py-2">Fecha</th>
            <th className="py-2">Formato</th>
            <th className="py-2">Vence</th>
            <th className="py-2 text-right">Monto</th>
            <th className="py-2 text-right">Pagado</th>
            <th className="py-2">Estado</th>
            <th className="py-2">Recibo</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map(invoice => {
            const warnings = warningsFor(invoice)
            return (
              <tr key={invoice.id} className="border-b align-top">
                <td className="py-2">
                  <Link className="underline" href={`/facturas/${invoice.id}`}>
                    {invoice.number}
                  </Link>
                  {invoice.arrival_count > 1 && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      llegó {invoice.arrival_count} veces
                    </span>
                  )}
                </td>
                <td className="py-2">
                  {invoice.supplier_name ?? (
                    <span className="text-warn">{invoice.supplier_text} · sin identificar</span>
                  )}
                </td>
                <td className="py-2">{day(invoice.issued_on)}</td>
                <td className="py-2">
                  {isScanned(invoice.file_kind) ? (
                    <span className="rounded bg-warn-surface px-1.5 py-0.5 text-xs text-warn">
                      {fileKindLabel(invoice.file_kind)}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">
                      {fileKindLabel(invoice.file_kind)}
                    </span>
                  )}
                </td>
                <td className="py-2">{day(invoice.due_on)}</td>
                <td className="py-2 text-right">{money(invoice.total)}</td>
                <td className="py-2 text-right">
                  {money(invoice.paid)}
                  {invoice.payment_state === 'PARCIAL' && (
                    <span className="ml-1 text-xs text-muted-foreground">{invoice.paid_pct}%</span>
                  )}
                </td>
                <td className="py-2">
                  {paymentStateLabel(invoice.payment_state)}
                  {warnings.map(warning => (
                    <p key={warning} className="text-xs text-warn">
                      {warning}
                    </p>
                  ))}
                </td>
                <td className="py-2">{invoice.receipt_issued ? 'Emitido' : 'Falta'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
