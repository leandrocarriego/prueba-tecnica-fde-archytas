'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { addDueDate, editDueDate, moveDueDate, removeDueDate } from '@/app/actions/purchases'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useLiveCalendar } from '@/components/purchases/useLiveCalendar'
import { day, money } from '@/lib/format'
import type { Calendar, DueDate } from '@/lib/purchases/types'

/**
 * Un mes del calendario, con lo que vence cada día.
 *
 * **Se actualiza solo** (H5): lo que otra persona agrega, corrige, mueve o
 * elimina llega por el canal en vivo y la pantalla se vuelve a pedir al
 * servidor, diciendo quién lo hizo. Si el canal se corta, lo dice en lugar de
 * seguir mostrando una foto vieja con cara de actual.
 *
 * Una fecha ya pasada vuelve rechazada la primera vez y se acepta al confirmar,
 * que es lo que RF-25 pide.
 *
 * Lo que viene de una factura no ofrece «eliminar»: la factura existe, y el día
 * en que vence también (RF-18).
 */
/** Cuántos vencimientos de un día se muestran antes de recortar (RF-08). */
const PER_DAY = 4

/** Cómo se lee cada verbo del canal en una frase de una línea. */
const VERBOS: Record<string, string> = {
  added: 'agregó',
  edited: 'corrigió',
  moved: 'movió',
  removed: 'eliminó',
}

export function CalendarGrid({ calendar, canEdit }: { calendar: Calendar; canEdit: boolean }) {
  const router = useRouter()
  const { state: live, lastChange } = useLiveCalendar()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [onDate, setOnDate] = useState('')
  const [description, setDescription] = useState('')
  const [amount, setAmount] = useState('')
  // Qué entrada se está moviendo o corrigiendo, y cuál se está arrastrando.
  const [moving, setMoving] = useState<number | null>(null)
  const [editing, setEditing] = useState<number | null>(null)
  const [dragging, setDragging] = useState<number | null>(null)
  // Los días que la persona pidió ver enteros (RF-08).
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

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

  /**
   * Mover una entrada a otra fecha.
   *
   * Arrastrarla y elegir la fecha en el selector terminan acá: para el sistema
   * es la misma decisión, y cómo la dijo la persona es asunto del navegador.
   */
  async function move(entry: DueDate, next: string, reason: string | null) {
    const first = await moveDueDate(entry.id, next, reason)
    if (first.ok) {
      setMoving(null)
      router.refresh()
      return
    }
    if (first.message.includes('ya pasó')) {
      // RF-25: se pregunta antes, y la respuesta vuelve como confirmación.
      if (window.confirm('La fecha nueva ya pasó. ¿Lo movés igual?')) {
        if (await run(() => moveDueDate(entry.id, next, reason, true))) setMoving(null)
      }
      return
    }
    setError(first.message)
  }

  /** Soltar una tarjeta sobre un día es moverla a ese día (RF-19). */
  async function drop(date: string) {
    const entry = calendar.items.find(item => item.id === dragging)
    setDragging(null)
    if (entry === undefined || entry.on_date === date) return
    await move(entry, date, null)
  }

  const cambio =
    lastChange === null
      ? null
      : `${lastChange.actorName || 'Alguien'} ${VERBOS[lastChange.action] ?? 'cambió'} un vencimiento`

  return (
    <div className="space-y-6">
      {/*
        El estado del canal, dicho en una línea. Que se corte no es un error de
        la persona ni algo que pueda arreglar: lo que necesita saber es que lo
        que está mirando puede haber quedado viejo, porque sobre esta pantalla
        se toman decisiones entre dos.
      */}
      {live === 'caido' && (
        <p className="rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          Se cortó la conexión en vivo: lo que ves puede estar desactualizado. Se está reintentando
          solo.
        </p>
      )}

      {live === 'en-vivo' && cambio !== null && (
        <p className="rounded border border-sky-300 bg-sky-50 p-3 text-sm text-sky-900">
          {cambio}. La pantalla ya se actualizó.
        </p>
      )}

      {error && (
        <p className="rounded border border-danger-border bg-danger-surface p-3 text-sm text-danger">
          {error}
        </p>
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
              <li
                key={date}
                className="space-y-2 rounded p-1 transition-colors data-[over=true]:bg-sky-50"
                data-over={dragging !== null}
                onDragOver={event => event.preventDefault()}
                onDrop={() => void drop(date)}
              >
                <h3 className="text-sm font-medium text-muted-foreground">{day(date)}</h3>
                <ul className="space-y-2">
                  {(expanded.has(date) ? entries : entries.slice(0, PER_DAY)).map(entry => (
                    <li
                      key={entry.id}
                      draggable={canEdit}
                      onDragStart={() => setDragging(entry.id)}
                      onDragEnd={() => setDragging(null)}
                      className={`rounded border p-3 text-sm ${canEdit ? 'cursor-grab' : ''} ${
                        entry.is_overdue_without_receipt
                          ? 'border-danger-border bg-danger-surface'
                          : ''
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
                        {entry.created_by_name &&
                          ` · lo cargó ${entry.created_by_name}${
                            entry.created_at ? ` el ${day(entry.created_at)}` : ''
                          }`}
                      </p>
                      {(entry.changes ?? []).length > 0 && (
                        <ul className="mt-1 text-xs text-muted-foreground">
                          {(entry.changes ?? []).map(change => (
                            <li key={change.id}>
                              {day(change.previous_date)} → {day(change.new_date)}
                              {change.actor_name ? ` · lo movió ${change.actor_name}` : ''}
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
                              onClick={() => setMoving(moving === entry.id ? null : entry.id)}
                            >
                              Mover
                            </Button>
                            {entry.origin === 'MANUAL' && (
                              <>
                                <Button
                                  type="button"
                                  variant="outline"
                                  disabled={busy}
                                  onClick={() => setEditing(editing === entry.id ? null : entry.id)}
                                >
                                  Corregir
                                </Button>
                                <Button
                                  type="button"
                                  variant="outline"
                                  disabled={busy}
                                  onClick={() => void run(() => removeDueDate(entry.id))}
                                >
                                  Eliminar
                                </Button>
                              </>
                            )}
                          </>
                        )}
                      </div>

                      {/*
                        Elegir la fecha en un selector, que es como H8 pide que
                        se pruebe. Antes se escribía a mano en un `prompt`, y una
                        fecha escrita a mano es una fecha que se puede tipear mal
                        justo cuando el punto de la pantalla es no equivocarse de
                        día.
                      */}
                      {moving === entry.id && (
                        <form
                          className="mt-2 flex flex-wrap items-end gap-2"
                          onSubmit={event => {
                            event.preventDefault()
                            const form = event.currentTarget
                            const date = (form.elements.namedItem('fecha') as HTMLInputElement)
                              .value
                            const why = (form.elements.namedItem('motivo') as HTMLInputElement)
                              .value
                            if (date) void move(entry, date, why || null)
                          }}
                        >
                          <label className="text-xs">
                            Fecha nueva
                            <Input name="fecha" type="date" defaultValue={entry.on_date} />
                          </label>
                          <label className="text-xs">
                            Motivo, si querés
                            <Input name="motivo" placeholder="Opcional" />
                          </label>
                          <Button type="submit" disabled={busy}>
                            Mover
                          </Button>
                          <Button type="button" variant="outline" onClick={() => setMoving(null)}>
                            Cancelar
                          </Button>
                        </form>
                      )}

                      {/* RF-15: corregir sin tener que borrar y volver a cargar. */}
                      {editing === entry.id && (
                        <form
                          className="mt-2 flex flex-wrap items-end gap-2"
                          onSubmit={event => {
                            event.preventDefault()
                            const form = event.currentTarget
                            const desc = (form.elements.namedItem('desc') as HTMLInputElement).value
                            const monto = (form.elements.namedItem('monto') as HTMLInputElement)
                              .value
                            void run(() => editDueDate(entry.id, desc || null, monto || null)).then(
                              ok => {
                                if (ok) setEditing(null)
                              }
                            )
                          }}
                        >
                          <label className="text-xs">
                            Descripción
                            <Input name="desc" defaultValue={entry.description} />
                          </label>
                          <label className="text-xs">
                            Monto
                            <Input
                              name="monto"
                              inputMode="decimal"
                              defaultValue={entry.amount ?? ''}
                            />
                          </label>
                          <Button type="submit" disabled={busy}>
                            Guardar
                          </Button>
                          <Button type="button" variant="outline" onClick={() => setEditing(null)}>
                            Cancelar
                          </Button>
                        </form>
                      )}
                    </li>
                  ))}
                </ul>
                {/*
                  RF-08: un día con más de los que entran dice cuántos hay y
                  deja verlos. El recorte existe para que un día cargado no
                  empuje los demás fuera de la pantalla, que es lo que un
                  calendario tiene que evitar por definición.
                */}
                {entries.length > PER_DAY && (
                  <button
                    type="button"
                    className="text-xs underline"
                    onClick={() =>
                      setExpanded(current => {
                        const next = new Set(current)
                        if (next.has(date)) next.delete(date)
                        else next.add(date)
                        return next
                      })
                    }
                  >
                    {expanded.has(date)
                      ? 'Ver menos'
                      : `y ${entries.length - PER_DAY} más en este día`}
                  </button>
                )}
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
