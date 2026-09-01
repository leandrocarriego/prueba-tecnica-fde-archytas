import Link from 'next/link'

import { Code, Day, Money } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Empty } from '@/components/ui/state'
import { fileKindLabel, isScanned, paymentStateLabel, warningsFor } from '@/lib/purchases/labels'
import type { Invoice } from '@/lib/purchases/types'
import { dueDateTone, invoicePaymentTone } from '@/lib/ui/tone'

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
 *
 * **Los estados son píldoras y salen del mapa único** (`RF-06`): «Venció sin
 * recibo» acá, en el calendario y en la ficha del proveedor es la misma píldora
 * roja, porque las tres la piden a `lib/ui/tone.ts` en vez de elegir su color.
 */
export function InvoiceTable({ invoices }: { invoices: Invoice[] }) {
  if (invoices.length === 0) {
    return <Empty title="No hay facturas que coincidan con lo que buscás." />
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b text-left text-muted-foreground">
          {/*
            `px-3` en cada celda, y no sólo `py-2`: sin aire horizontal, una
            columna alineada a la derecha queda pegada a la de al lado y el
            encabezado se lee «PagadoEstado». Lo encontró el recorrido del
            `Tester` mirando la pantalla, no una aserción (`UI-08`).
          */}
          <tr>
            <th className="px-3 py-2 first:pl-0 last:pr-0">Factura</th>
            <th className="px-3 py-2">Proveedor</th>
            <th className="px-3 py-2">Fecha</th>
            <th className="px-3 py-2">Formato</th>
            <th className="px-3 py-2">Vence</th>
            <th className="px-3 py-2 text-right">Monto</th>
            <th className="px-3 py-2 text-right">Pagado</th>
            <th className="px-3 py-2">Estado</th>
            <th className="px-3 py-2 last:pr-0">Recibo</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map(invoice => {
            /*
             * Lo que venció sin recibo lo dice la píldora de la última columna,
             * así que se saca de las advertencias: dicho dos veces en la misma
             * fila, la segunda deja de leerse.
             *
             * Se filtra por el **comienzo** del texto y no por igualdad: la
             * píldora dice «Venció sin recibo» y la advertencia «Venció sin
             * recibo de recepción», así que comparar los dos completos no
             * coincidía nunca y la fila lo decía dos veces igual. Lo encontró
             * el recorrido del `Tester`, mirando la pantalla.
             */
            const warnings = warningsFor(invoice).filter(
              warning => !warning.startsWith('Venció sin recibo')
            )
            const recibo = dueDateTone({ ...invoice, is_past: false })
            return (
              <tr
                key={invoice.id}
                className="border-b align-top [&>*]:px-3 [&>*:first-child]:pl-0 [&>*:last-child]:pr-0"
              >
                {/* Un código no se parte en dos renglones: se compara de un vistazo. */}
                <td className="py-2 whitespace-nowrap">
                  <Link className="text-link hover:underline" href={`/facturas/${invoice.id}`}>
                    <Code value={invoice.number} />
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
                <Day value={invoice.issued_on} cell className="py-2 text-left" />
                <td className="py-2">
                  {isScanned(invoice.file_kind) ? (
                    <Badge tone="warn">{fileKindLabel(invoice.file_kind)}</Badge>
                  ) : (
                    <span className="text-muted-foreground">
                      {fileKindLabel(invoice.file_kind)}
                    </span>
                  )}
                </td>
                <Day value={invoice.due_on} cell className="py-2 text-left" />
                <Money value={invoice.total} cell className="py-2" />
                <td className="py-2 text-right">
                  <Money value={invoice.paid} />
                  {invoice.payment_state === 'PARCIAL' && (
                    <span className="ml-1 text-xs text-muted-foreground">{invoice.paid_pct}%</span>
                  )}
                </td>
                <td className="py-2">
                  <Badge tone={invoicePaymentTone(invoice.payment_state)}>
                    {paymentStateLabel(invoice.payment_state)}
                  </Badge>
                  {warnings.map(warning => (
                    <p key={warning} className="mt-1 text-xs text-warn">
                      {warning}
                    </p>
                  ))}
                </td>
                <td className="py-2">
                  {recibo ? <Badge tone={recibo.tone}>{recibo.label}</Badge> : <Badge>Falta</Badge>}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
