'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { addDueDate, moveDueDate, removeDueDate } from '@/app/actions/purchases'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { day, money } from '@/lib/format'
import type { Calendar, DueDate } from '@/lib/purchases/types'

/**
 * Un mes del calendario, con lo que vence cada día.
 *
 * Mover un vencimiento se hace **eligiendo la fecha nueva**, que es RF-42, y el
 * arrastre de RF-19 es la misma llamada con otra forma de decirlo. Una fecha ya
 * pasada vuelve rechazada la primera vez y se acepta al confirmar, que es lo que
 * RF-25 pide.
 *
 * Lo que viene de una factura no ofrece «eliminar»: la factura existe, y el día
 * en que vence también (RF-18).
 */
export function CalendarGrid({ calendar, canEdit }: { calendar: Calendar; canEdit: boolean }) {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [onDate, setOnDate] = useState('')
  const [description, setDescription] = useState('')
  const [amount, setAmount] = useState('')

  const byDay = new Map<string, DueDate[]>()
  for (const entry of calendar.items) {
    byDay.set(entry.on_date, [...(byDay.get(entry.on_date) ?? []), entry])
  }

  async function run(action: () => Promise<{ ok: boolean; message?: string }>) {
    setBusy(true)
    setError(null)
    const result = await action()
    setBusy(false)
    if (result.ok) {
      router.refresh()
      return true
    }
    setError(result.message ?? 'No se pudo guardar')
    return false
  }

  async function move(entry: DueDate) {
    const next = window.prompt('Fecha nueva (aaaa-mm-dd)', entry.on_date)
    if (!next) return
    const reason = window.prompt('Motivo (opcional)') ?? null
    const first = await moveDueDate(entry.id, next, reason)
    if (first.ok) {
      router.refresh()
      return
    }
    if (first.message.includes('ya pasó')) {
      if (window.confirm('La fecha nueva ya pasó. ¿Lo movés igual?')) {
        await run(() => moveDueDate(entry.id, next, reason, true))
      }
      return
    }
    setError(first.message)
  }

  return (
    <div className="space-y-6">
      {error && (
        <p className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-900">{error}</p>
      )}

      {byDay.size === 0 ? (
        <p className="rounded border border-dashed p-8 text-center text-muted-foreground">
          No vence nada en este período.
        </p>
      ) : (
        <ol className="space-y-4">
          {[...byDay.entries()]
            .sort(([left], [right]) => left.localeCompare(right))
            .map(([date, entries]) => (
              <li key={date} className="space-y-2">
                <h3 className="text-sm font-medium text-muted-foreground">{day(date)}</h3>
                <ul className="space-y-2">
                  {entries.map(entry => (
                    <li
                      key={entry.id}
                      className={`rounded border p-3 text-sm ${
                        entry.is_overdue_without_receipt ? 'border-red-300 bg-red-50' : ''
                      }`}
                    >
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <span className="font-medium">{entry.description}</span>
                        <span>{money(entry.amount)}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {entry.origin === 'INVOICE' ? 'De una factura' : 'Cargado a mano'}
                        {entry.is_past && ' · ya pasó'}
                        {entry.was_rescheduled &&
                          ` · reprogramado, original ${day(entry.original_date)}`}
                        {entry.receipt_issued && ' · recibo emitido'}
                        {entry.is_overdue_without_receipt && ' · venció sin recibo'}
                        {entry.payment_state && ` · ${entry.payment_state.toLowerCase()}`}
                      </p>
                      {(entry.changes ?? []).length > 0 && (
                        <ul className="mt-1 text-xs text-muted-foreground">
                          {(entry.changes ?? []).map(change => (
                            <li key={change.id}>
                              {day(change.previous_date)} → {day(change.new_date)}
                              {change.reason ? ` · ${change.reason}` : ''}
                            </li>
                          ))}
                        </ul>
                      )}
                      <div className="mt-2 flex flex-wrap gap-2">
                        {entry.invoice_id && (
                          <a className="text-xs underline" href={`/facturas/${entry.invoice_id}`}>
                            Ver la factura
                          </a>
                        )}
                        {canEdit && (
                          <>
                            <Button
                              type="button"
                              variant="outline"
                              disabled={busy}
                              onClick={() => void move(entry)}
                            >
                              Mover
                            </Button>
                            {entry.origin === 'MANUAL' && (
                              <Button
                                type="button"
                                variant="outline"
                                disabled={busy}
                                onClick={() => void run(() => removeDueDate(entry.id))}
                              >
                                Eliminar
                              </Button>
                            )}
                          </>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
        </ol>
      )}

      {canEdit && (
        <form
          className="flex flex-wrap items-end gap-2 border-t pt-4"
          onSubmit={event => {
            event.preventDefault()
            void run(() => addDueDate(onDate, description, amount || null)).then(ok => {
              if (ok) {
                setOnDate('')
                setDescription('')
                setAmount('')
              }
            })
          }}
        >
          <label className="text-sm">
            <span className="mb-1 block text-muted-foreground">Fecha</span>
            <Input
              type="date"
              value={onDate}
              onChange={event => setOnDate(event.target.value)}
              required
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-muted-foreground">Qué vence</span>
            <Input
              value={description}
              onChange={event => setDescription(event.target.value)}
              required
              maxLength={300}
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-muted-foreground">Monto</span>
            <Input value={amount} onChange={event => setAmount(event.target.value)} />
          </label>
          <Button type="submit" disabled={busy}>
            Agregar vencimiento
          </Button>
        </form>
      )}
    </div>
  )
}
