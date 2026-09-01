'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

import { splitPayment } from '@/app/actions/purchases'
import { Code, Day, Money } from '@/components/ui/amount'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Notice } from '@/components/ui/notice'
import { Empty } from '@/components/ui/state'
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
    <Card className="space-y-4 p-5">
      <header className="space-y-1">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <Money value={payment.amount} as="div" className="text-lg font-medium" />
          <span className="text-sm text-muted-foreground">
            Pagado el <Day value={payment.paid_on} />
          </span>
        </div>
        <p className="text-sm text-muted-foreground">
          {payment.supplier_text || 'Sin proveedor identificado'}
          {payment.reference && ` · ${payment.reference}`}
        </p>
        {/*
         * Por qué quedó apartado, arriba del reparto que lo resuelve: el aviso
         * va antes que el número que califica (`RF-14`), y su salida es el
         * formulario de abajo.
         */}
        {payment.review_reason && <Notice tone="warn" title={payment.review_reason} />}
      </header>

      {/*
        Sin proveedor resuelto no hay facturas entre las cuales repartir, y
        elegirlas de todo el sistema sería ofrecer las de otro proveedor: el
        supuesto firmado dice que un comprobante cubre facturas de uno solo.
      */}
      {invoices.length === 0 ? (
        <Empty title="Todavía no hay facturas de este proveedor donde imputarlo.">
          Cuando entren, van a aparecer acá.
        </Empty>
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
                    <Link className="text-link hover:underline" href={`/facturas/${invoice.id}`}>
                      <Code value={invoice.number} />
                    </Link>
                  </td>
                  <Day value={invoice.due_on} cell className="py-2 text-left" />
                  <Money value={invoice.total} cell className="py-2" />
                  <Money value={invoice.balance} cell className="py-2" />
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
              Repartido <Money value={assigned} /> de <Money value={payment.amount} />.{' '}
              {exact ? (
                <span className="text-ok">Cierra exacto.</span>
              ) : (
                <span className="text-muted-foreground">
                  {left > 0 ? (
                    <>
                      Falta repartir <Money value={left} />.
                    </>
                  ) : (
                    <>
                      Te pasaste por <Money value={-left} />.
                    </>
                  )}
                </span>
              )}
            </p>
            {/* Repartir es la tarea de esta pantalla: su único naranja (`RF-11`). */}
            <Button
              type="button"
              variant="brand"
              disabled={busy || !exact}
              onClick={() => void confirm()}
            >
              Confirmar el reparto
            </Button>
          </div>
        </>
      )}

      {error && <Notice tone="danger" title={error} />}
    </Card>
  )
}
