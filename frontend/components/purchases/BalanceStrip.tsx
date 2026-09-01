import { Money } from '@/components/ui/amount'
import { count } from '@/lib/format'
import type { Invoice } from '@/lib/purchases/types'

/**
 * Los tres estados en que puede estar una factura frente a su pago, y el color
 * con el que la guía los dibuja en la barra (`3c`).
 *
 * Salen de `payment_state`, que el backend **calcula** con los pagos imputados y
 * nunca toma de lo que informa el portal (RF-45 de 005). `INCONSISTENTE` —una
 * factura con más pagos que total— no está entre los tres: no es un tramo del
 * saldo, es un error, y meterlo en la barra lo dibujaría como si fuera parte
 * normal de la composición.
 */
const SEGMENTS = [
  { state: 'SALDADA', label: 'Saldadas', fill: 'bg-ok', dot: 'bg-ok' },
  { state: 'PARCIAL', label: 'Parciales', fill: 'bg-info', dot: 'bg-info' },
  { state: 'SIN_PAGOS', label: 'Sin tocar', fill: 'bg-brand', dot: 'bg-brand' },
] as const

/**
 * El estado del saldo de una cuenta corriente, como una sola barra (guía `3c`).
 *
 * Es la pregunta con la que se abre la ficha de un proveedor —*¿cómo venimos
 * con éste?*— contestada antes que cualquier fila: qué proporción de lo que le
 * compramos está saldado, a medias, o sin tocar.
 *
 * **Mide facturas y no plata**, y el rótulo lo dice. Es la lectura que se puede
 * verificar mirando la tabla de abajo, que es la única clase de número que estas
 * pantallas escriben: contar importes daría una barra distinta de la lista que
 * la acompaña y nadie podría explicar la diferencia.
 *
 * Los porcentajes se redondean para leerse, y por eso pueden no dar cien
 * exactos; los anchos, en cambio, salen de la proporción sin redondear, así que
 * la barra siempre cierra aunque los rótulos digan 71, 17 y 12.
 */
export function BalanceStrip({ invoices, total }: { invoices: Invoice[]; total: string | number }) {
  const counted = invoices.filter(invoice =>
    SEGMENTS.some(segment => segment.state === invoice.payment_state)
  )
  if (counted.length === 0) return null

  const parts = SEGMENTS.map(segment => ({
    ...segment,
    howMany: counted.filter(invoice => invoice.payment_state === segment.state).length,
  })).map(segment => ({
    ...segment,
    share: (segment.howMany / counted.length) * 100,
  }))

  return (
    <div className="space-y-2.5 border-b border-border px-4 py-3.5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-[13px] text-muted-foreground">
          Estado del saldo de las {count(counted.length)}{' '}
          {counted.length === 1 ? 'factura' : 'facturas'} del período
        </p>
        <p className="amount text-[13px] text-foreground">
          <Money value={total} as="span" /> total
        </p>
      </div>

      {/* La barra es la lectura; la leyenda de abajo es la que se puede oír. */}
      <div aria-hidden className="flex h-2.5 overflow-hidden rounded-full bg-muted">
        {parts.map(part =>
          part.share > 0 ? (
            <span key={part.state} className={part.fill} style={{ width: `${part.share}%` }} />
          ) : null
        )}
      </div>

      <ul className="flex flex-wrap items-center gap-x-4 gap-y-1">
        {parts.map(part => (
          <li key={part.state} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span aria-hidden className={`size-2 rounded-full ${part.dot}`} />
            {part.label} {Math.round(part.share)} %
          </li>
        ))}
      </ul>
    </div>
  )
}
