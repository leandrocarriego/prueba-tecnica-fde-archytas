'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { issueReceipt, registerPayment, voidPayment, voidReceipt } from '@/app/actions/purchases'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { formatMoment } from '@/lib/catalog/format'
import { day, money } from '@/lib/format'
import type { Invoice, Payment, Receipt } from '@/lib/purchases/types'

/**
 * Lo que se hace sobre una factura: cargar un pago, y emitir o anular su recibo.
 *
 * Un pago que supera el saldo vuelve rechazado la primera vez con el saldo en
 * el mensaje — **ese es el aviso de RF-21** — y se contesta apretando de nuevo,
 * que es lo que hace el botón de confirmar. Un pago traído del portal no ofrece
 * deshacer, porque es lo que informó el origen (RF-23).
 */
export function InvoicePanel({
  invoice,
  payments,
  receipt,
  canPay,
  canIssue,
}: {
  invoice: Invoice
  payments: Payment[]
  receipt: Receipt | null
  canPay: boolean
  canIssue: boolean
}) {
  const router = useRouter()
  const [amount, setAmount] = useState('')
  const [paidOn, setPaidOn] = useState('')
  const [reference, setReference] = useState('')
  const [warning, setWarning] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function run(action: () => Promise<{ ok: boolean; message?: string }>) {
    setBusy(true)
    setError(null)
    const result = await action()
    setBusy(false)
    if (result.ok) {
      setWarning(null)
      setAmount('')
      setReference('')
      router.refresh()
      return true
    }
    setError(result.message ?? 'No se pudo guardar')
    return false
  }

  async function pay(confirmOverBalance: boolean) {
    setError(null)
    const result = await registerPayment(
      invoice.id,
      amount,
      paidOn,
      reference || null,
      confirmOverBalance
    )
    if (result.ok) {
      setWarning(null)
      setAmount('')
      setReference('')
      router.refresh()
      return
    }
    if (!confirmOverBalance && result.message.includes('supera el saldo')) {
      setWarning(`${result.message}. Si querés registrarlo igual, confirmá.`)
      return
    }
    setError(result.message)
  }

  return (
    <div className="space-y-6">
      {error && (
        <p className="rounded border border-danger-border bg-danger-surface p-3 text-sm text-danger">
          {error}
        </p>
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Pagos imputados</h2>
        {payments.length === 0 ? (
          <p className="text-sm text-muted-foreground">Todavía no tiene ningún pago imputado.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b text-left text-muted-foreground">
              <tr>
                <th className="py-2">Fecha</th>
                <th className="py-2 text-right">Monto</th>
                <th className="py-2">Origen</th>
                <th className="py-2">Estado</th>
                {canPay && <th className="py-2" />}
              </tr>
            </thead>
            <tbody>
              {payments.map(payment => (
                <tr key={payment.id} className="border-b">
                  <td className="py-2">{day(payment.paid_on)}</td>
                  <td className="py-2 text-right">{money(payment.amount)}</td>
                  <td className="py-2">
                    {payment.origin === 'PORTAL' ? 'Del portal' : 'Cargado a mano'}
                  </td>
                  <td className="py-2">{payment.state === 'VOIDED' ? 'Sin efecto' : 'Imputado'}</td>
                  {canPay && (
                    <td className="py-2 text-right">
                      {payment.origin === 'MANUAL' && payment.state !== 'VOIDED' && (
                        <Button
                          type="button"
                          variant="outline"
                          disabled={busy}
                          onClick={() => void run(() => voidPayment(payment.id, invoice.id))}
                        >
                          Dejar sin efecto
                        </Button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {canPay && (
          <form
            className="flex flex-wrap items-end gap-2"
            onSubmit={event => {
              event.preventDefault()
              void pay(false)
            }}
          >
            <label className="text-sm">
              <span className="mb-1 block text-muted-foreground">Monto</span>
              <Input value={amount} onChange={event => setAmount(event.target.value)} required />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-muted-foreground">Fecha del pago</span>
              <Input
                type="date"
                value={paidOn}
                onChange={event => setPaidOn(event.target.value)}
                required
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-muted-foreground">Comprobante</span>
              <Input value={reference} onChange={event => setReference(event.target.value)} />
            </label>
            <Button type="submit" disabled={busy}>
              Registrar pago
            </Button>
          </form>
        )}

        {warning && (
          <div className="space-y-2 rounded border border-warn-border bg-warn-surface p-3 text-sm text-warn">
            <p>{warning}</p>
            <Button type="button" variant="outline" disabled={busy} onClick={() => void pay(true)}>
              Registrarlo igual
            </Button>
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Recibo de recepción</h2>
        {receipt ? (
          <div className="space-y-2 text-sm">
            <p>
              {receipt.number} · emitido el {formatMoment(receipt.issued_at)}
            </p>
            <pre className="overflow-x-auto rounded bg-muted p-3 text-xs">{receipt.document}</pre>
            {canIssue && (
              <Button
                type="button"
                variant="outline"
                disabled={busy}
                onClick={() => void run(() => voidReceipt(receipt.id, invoice.id))}
              >
                Anular el recibo
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-2 text-sm">
            <p className="text-muted-foreground">
              {invoice.is_overdue_without_receipt
                ? 'La factura venció sin recibo: ya no se le puede emitir uno.'
                : 'Todavía no tiene recibo emitido.'}
            </p>
            {canIssue && !invoice.is_overdue_without_receipt && (
              <Button
                type="button"
                disabled={busy}
                onClick={() => void run(() => issueReceipt(invoice.id))}
              >
                Emitir el recibo
              </Button>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
