import Link from 'next/link'

import { Code, Day, Money } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import type { UpcomingDue } from '@/lib/purchases/types'

/**
 * Los próximos vencimientos, con la forma de tabla de la guía visual (`3b`):
 * proveedor, factura, monto, cuándo vence y si tiene recibo.
 *
 * **El monto es el saldo, no el total de la factura.** Es la diferencia entre
 * decirle a alguien lo que debe y decirle que pague de nuevo algo que ya pagó
 * a medias.
 *
 * «Vence» se dice en días y no en fecha porque es lo que se decide con eso —«en
 * 2 días» se lee sin restar—, y la fecha viaja igual, abajo, para quien la
 * necesita. Lo que vence en dos días o menos va en rojo: no es decoración, es
 * el único caso en que hay que hacer algo hoy.
 */
export function UpcomingDues({ dues }: { dues: UpcomingDue[] }) {
  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between gap-4 border-b border-border px-5 py-3.5">
        <h2 className="text-base font-semibold text-foreground">Próximos vencimientos</h2>
        <Link className="text-[13px] font-semibold text-link hover:underline" href="/calendario">
          Ver calendario →
        </Link>
      </div>

      {dues.length === 0 ? (
        <p className="px-5 py-8 text-center text-sm text-muted-foreground">
          No hay ninguna factura con saldo por vencer.
        </p>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-muted">
              <th className="section-label px-5 py-2.5 text-left">Proveedor</th>
              <th className="section-label px-5 py-2.5 text-left">Factura</th>
              <th className="section-label px-5 py-2.5 text-right">Saldo</th>
              <th className="section-label px-5 py-2.5 text-left">Vence</th>
              <th className="section-label px-5 py-2.5 text-left">Recibo</th>
            </tr>
          </thead>
          <tbody>
            {dues.map(due => (
              <tr key={due.invoice_id} className="border-b border-border last:border-0">
                <td className="px-5 py-3 text-[13px] text-foreground">
                  {/*
                    A la factura y no al proveedor: lo que alguien hace con una
                    fila de esta lista es abrir la factura que vence —ver el
                    documento, imputar el pago, emitir el recibo—, y la ficha
                    del proveedor es otro viaje.
                  */}
                  <Link
                    className="hover:text-link hover:underline"
                    href={`/facturas/${due.invoice_id}`}
                  >
                    {due.supplier_name ?? due.supplier_text}
                  </Link>
                  {/*
                    Sin proveedor resuelto el importe no está confirmado, y la
                    píldora punteada es exactamente eso en toda la aplicación
                    (`UI-03`): leído del origen, todavía sin confirmar.
                  */}
                  {due.in_review && (
                    <Badge tone="draft" className="ml-2">
                      Sin confirmar
                    </Badge>
                  )}
                </td>
                <Code value={due.number} cell className="px-5 py-3 text-left text-[13px]" />
                <Money value={due.balance} cell className="px-5 py-3 text-[13px]" />
                <td className="px-5 py-3 text-[13px]">
                  <span className={due.days_left <= 2 ? 'font-semibold text-danger' : ''}>
                    {when(due.days_left)}
                  </span>
                  <Day
                    value={due.due_on}
                    as="span"
                    className="ml-2 text-xs text-muted-foreground"
                  />
                </td>
                <td className="px-5 py-3">
                  {due.receipt_issued ? (
                    <Badge tone="ok">ok</Badge>
                  ) : (
                    <Badge tone="warn">falta</Badge>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

/** Cuánto falta, dicho como lo diría una persona. */
function when(days: number): string {
  if (days < 0) return days === -1 ? 'venció ayer' : `venció hace ${Math.abs(days)} días`
  if (days === 0) return 'vence hoy'
  if (days === 1) return 'en 1 día'
  return `en ${days} días`
}
