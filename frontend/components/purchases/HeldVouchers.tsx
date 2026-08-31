'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

import { splitPayment } from '@/app/actions/purchases'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { day, money } from '@/lib/format'
import type { Invoice, Payment } from '@/lib/purchases/types'

/**
 * Repartir un comprobante entre las facturas que cubre (RF-53 a RF-56).
 *
 * Tres reglas de la spec firmada están acá y ninguna es decoración:
 *
 * - **El reparto lo hace una persona, nunca el sistema.** No hay botón de
 *   "repartir automáticamente", ni sugerencia por monto: el campo arranca
 *   vacío y lo llena quien sabe.
 * - **Tiene que sumar exacto** (RF-55). Lo dice el total en vivo, y el backend
 *   lo vuelve a verificar: esto adelanta el rechazo, no lo reemplaza.
 * - **Hasta que se confirma, ningún saldo se mueve** (RF-54).
 */
export function HeldVouchers({
  held,
  invoicesBySupplier,
}: {
  held: Payment[]
  invoicesBySupplier: Record<number, Invoice[]>
}) {
  return (
    <div className="space-y-6">
      {held.map(payment => (
        <VoucherCard
          key={payment.id}
          payment={payment}
          invoices={
            payment.supplier_id === null ? [] : (invoicesBySupplier[payment.supplier_id] ?? [])
          }
        />
      ))}
    </div>
  )
}

function VoucherCard({ payment, invoices }: { payment: Payment; invoices: Invoice[] }) {
  const router = useRouter()
  const [parts, setParts] = useState<Record<number, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const total = Number(payment.amount)
  const assigned = Object.values(parts).reduce((sum, value) => {
    const amount = Number(value)
    return Number.isNaN(amount) ? sum : sum + amount
  }, 0)
  // La resta se hace en centavos para que 0.1 + 0.2 no impida confirmar un
  // reparto que suma bien.
  const left = Math.round((total - assigned) * 100) / 100
  const exact = left === 0 && assigned > 0

  function setPart(invoiceId: number, value: string) {
    setParts(current => ({ ...current, [invoiceId]: value }))
  }

  async function confirm() {
    setBusy(true)
    setError(null)
    const chosen = Object.entries(parts)
      .filter(([, value]) => value.trim() !== '' && Number(value) > 0)
      .map(([invoiceId, value]) => ({ invoice_id: Number(invoiceId), amount: value }))
    const result = await splitPayment(payment.id, chosen)
    setBusy(false)
    if (result.ok) {
      router.refresh()
      return
    }
    setError(result.message)
  }

  return (
    <article className="space-y-4 rounded border p-4">
      <header className="space-y-1">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-lg font-medium">{money(payment.amount)}</h2>
          <span className="text-sm text-muted-foreground">Pagado el {day(payment.paid_on)}</span>
        </div>
        <p className="text-sm text-muted-foreground">
          {payment.supplier_text || 'Sin proveedor identificado'}
          {payment.reference && ` · ${payment.reference}`}
        </p>
        {payment.review_reason && (
          <p className="rounded border border-warn-border bg-warn-surface p-2 text-sm text-warn">
            {payment.review_reason}
          </p>
        )}
      </header>

      {/*
        Sin proveedor resuelto no hay facturas entre las cuales repartir, y
        elegirlas de todo el sistema sería ofrecer las de otro proveedor: el
        supuesto firmado dice que un comprobante cubre facturas de uno solo.
      */}
      {invoices.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Todavía no hay facturas de este proveedor donde imputarlo. Cuando entren, van a aparecer
          acá.
        </p>
      ) : (
        <>
          <table className="w-full text-sm">
            <thead className="border-b text-left text-muted-foreground">
              <tr>
                <th className="py-2">Factura</th>
                <th className="py-2">Vence</th>
                <th className="py-2 text-right">Total</th>
                <th className="py-2 text-right">Saldo</th>
                <th className="py-2 text-right">Parte</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map(invoice => (
                <tr key={invoice.id} className="border-b">
                  <td className="py-2">
                    <Link className="underline" href={`/facturas/${invoice.id}`}>
                      {invoice.number}
                    </Link>
                  </td>
                  <td className="py-2">{invoice.due_on ? day(invoice.due_on) : '—'}</td>
                  <td className="py-2 text-right">{money(invoice.total)}</td>
                  <td className="py-2 text-right">{money(invoice.balance)}</td>
                  <td className="py-2 text-right">
                    <Input
                      className="w-28 text-right"
                      inputMode="decimal"
                      placeholder="0"
                      value={parts[invoice.id] ?? ''}
                      onChange={event => setPart(invoice.id, event.target.value)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm">
              Repartido {money(assigned)} de {money(payment.amount)}.{' '}
              {exact ? (
                <span className="text-ok">Cierra exacto.</span>
              ) : (
                <span className="text-muted-foreground">
                  {left > 0 ? `Falta repartir ${money(left)}.` : `Te pasaste por ${money(-left)}.`}
                </span>
              )}
            </p>
            <Button type="button" disabled={busy || !exact} onClick={() => void confirm()}>
              Confirmar el reparto
            </Button>
          </div>
        </>
      )}

      {error && (
        <p className="rounded border border-danger-border bg-danger-surface p-3 text-sm text-danger">
          {error}
        </p>
      )}
    </article>
  )
}
