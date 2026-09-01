'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { addDueDate, editDueDate, moveDueDate, removeDueDate } from '@/app/actions/purchases'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useLiveCalendar } from '@/components/purchases/useLiveCalendar'
import { day, money } from '@/lib/format'
import { PER_DAY, dayNumber, isInWindow, weeksOf } from '@/lib/purchases/calendar'
import { cn } from '@/lib/utils'
import type { Calendar, DueDate } from '@/lib/purchases/types'

/**
 * Un mes del calendario, con lo que vence cada día.
 *
 * **Es una grilla del mes** (RF-01), no una lista de los días que tienen algo:
 * un día sin vencimientos existe, vacío, y verlo vacío es parte de lo que se
 * viene a mirar. Elegir un día abre su detalle debajo, que es donde vive la
 * tarjeta entera con sus acciones — una celda de siete columnas no da para un
 * formulario, y apretarlo ahí sería empeorar las dos cosas.
 *
 * **En un teléfono no hay grilla** (RF-41): siete columnas en 390px no se leen.
 * Ahí la pantalla muestra los días con algo, uno debajo del otro, con la tarjeta
 * entera. Es la misma información con la forma que entra.
 *
 * **Se actualiza sola** (H5): lo que otra persona agrega, corrige, mueve o
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

/** Cómo se lee cada verbo del canal en una frase de una línea. */
const VERBOS: Record<string, string> = {
  added: 'agregó',
  edited: 'corrigió',
  moved: 'movió',
  removed: 'eliminó',
}

/** Los encabezados de la grilla, que empieza el lunes como la semana laboral. */
const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

/**
 * Lo que la pantalla necesita para operar sobre una tarjeta.
 *
 * Va en un objeto y no en ocho props sueltas porque las dos vistas —la grilla y
 * la lista del teléfono— dibujan exactamente la misma tarjeta, y lo que se
 * reparte entre dos lugares termina divergiendo.
 */
interface Acciones {
  canEdit: boolean
  busy: boolean
  moving: number | null
  editing: number | null
  setMoving: (id: number | null) => void
  setEditing: (id: number | null) => void
  setDragging: (id: number | null) => void
  run: (action: () => Promise<{ ok: boolean; message?: string }>) => Promise<boolean>
  move: (entry: DueDate, next: string, reason: string | null) => Promise<void>
}

/** Lo que se dibuja de un día, con su recorte y su «y N más» (RF-08). */
function DayEntries({
  date,
  entries,
  expanded,
  onToggle,
  acciones,
}: {
  date: string
  entries: DueDate[]
  expanded: boolean
  onToggle: (date: string) => void
  acciones: Acciones
}) {
  return (
    <>
      <ul className="space-y-2">
        {(expanded ? entries : entries.slice(0, PER_DAY)).map(entry => (
          <DueDateCard key={entry.id} entry={entry} acciones={acciones} />
        ))}
      </ul>
      {entries.length > PER_DAY && (
        <button type="button" className="text-xs underline" onClick={() => onToggle(date)}>
          {expanded ? 'Ver menos' : `y ${entries.length - PER_DAY} más en este día`}
        </button>
      )}
    </>
  )
}

/** Una tarjeta entera, con todo lo que la spec pide leer de un vencimiento. */
function DueDateCard({ entry, acciones }: { entry: DueDate; acciones: Acciones }) {
  const { canEdit, busy, moving, editing, setMoving, setEditing, setDragging, run, move } = acciones
  return (
    <li
      draggable={canEdit}
      onDragStart={() => setDragging(entry.id)}
      onDragEnd={() => setDragging(null)}
      className={cn(
        'rounded border p-3 text-sm',
        canEdit && 'cursor-grab',
        entry.is_overdue_without_receipt && 'border-danger-border bg-danger-surface'
      )}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-medium">{entry.description}</span>
        <span>{money(entry.amount)}</span>
      </div>
      <p className="text-xs text-muted-foreground">
        {/* RF-02: el proveedor, cuando el vencimiento tiene uno. */}
        {entry.supplier_name && `${entry.supplier_name} · `}
        {entry.origin === 'INVOICE' ? 'De una factura' : 'Cargado a mano'}
        {entry.is_past && ' · ya pasó'}
        {entry.was_rescheduled && ` · reprogramado, original ${day(entry.original_date)}`}
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
          Elegir la fecha en un selector, que es como H8 pide que se pruebe.
          Antes se escribía a mano en un `prompt`, y una fecha escrita a mano es
          una fecha que se puede tipear mal justo cuando el punto de la pantalla
          es no equivocarse de día.
        */}
      {moving === entry.id && (
        <form
          className="mt-2 flex flex-wrap items-end gap-2"
          onSubmit={event => {
            event.preventDefault()
            const form = event.currentTarget
            const date = (form.elements.namedItem('fecha') as HTMLInputElement).value
            const why = (form.elements.namedItem('motivo') as HTMLInputElement).value
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
            const monto = (form.elements.namedItem('monto') as HTMLInputElement).value
            void run(() => editDueDate(entry.id, desc || null, monto || null)).then(ok => {
              if (ok) setEditing(null)
            })
          }}
        >
          <label className="text-xs">
            Descripción
            <Input name="desc" defaultValue={entry.description} />
          </label>
          <label className="text-xs">
            Monto
            <Input name="monto" inputMode="decimal" defaultValue={entry.amount ?? ''} />
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
  )
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
  const conAlgo = [...byDay.keys()].sort()

  // El día abierto en la grilla. Arranca en el primero que tenga algo, para que
  // la pantalla llegue con detalle en vez de con una invitación a hacer clic.
  const [selected, setSelected] = useState<string | null>(conAlgo[0] ?? null)
  const abierto = selected !== null && byDay.has(selected) ? selected : (conAlgo[0] ?? null)

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

  /** Abrir o cerrar un día cargado (RF-08). */
  function toggleExpanded(date: string) {
    setExpanded(current => {
      const next = new Set(current)
      if (next.has(date)) next.delete(date)
      else next.add(date)
      return next
    })
  }

  const acciones: Acciones = {
    canEdit,
    busy,
    moving,
    editing,
    setMoving,
    setEditing,
    setDragging,
    run,
    move,
  }

  const cambio =
    lastChange === null
      ? null
      : `${lastChange.actorName || 'Alguien'} ${VERBOS[lastChange.action] ?? 'cambió'} un vencimiento`

  const semanas = weeksOf(calendar.since, calendar.until)

  return (
    <div className="space-y-6">
      {/*
        El estado del canal, dicho en una línea. Que se corte no es un error de
        la persona ni algo que pueda arreglar: lo que necesita saber es que lo
        que está mirando puede haber quedado viejo, porque sobre esta pantalla
        se toman decisiones entre dos.
      */}
      {live === 'caido' && (
        <p className="rounded border border-warn-border bg-warn-surface p-3 text-sm text-warn">
          Se cortó la conexión en vivo: lo que ves puede estar desactualizado. Se está reintentando
          solo.
        </p>
      )}

      {live === 'en-vivo' && cambio !== null && (
        <p className="rounded border border-info-border bg-info-surface p-3 text-sm text-info">
          {cambio}. La pantalla ya se actualizó.
        </p>
      )}

      {error && (
        <p className="rounded border border-danger-border bg-danger-surface p-3 text-sm text-danger">
          {error}
        </p>
      )}

      {/*
        La grilla del mes, desde una pantalla ancha. Cada día es una celda —haya
        o no algo ese día— y soltar una tarjeta sobre una celda la mueve a ese
        día, que es RF-19 dicho en la forma en que un calendario lo dice.
      */}
      <div className="hidden md:block">
        <div className="grid grid-cols-7 gap-px text-xs font-medium text-muted-foreground">
          {DIAS.map(nombre => (
            <div key={nombre} className="px-2 pb-1">
              {nombre}
            </div>
          ))}
        </div>
        <ol
          aria-label="El mes, día por día"
          className="grid grid-cols-7 gap-px rounded border bg-border"
        >
          {semanas.flat().map(date => {
            const entries = byDay.get(date) ?? []
            const dentro = isInWindow(date, calendar.since, calendar.until)
            return (
              <li key={date} className="contents">
                <button
                  type="button"
                  // Un día fuera de la ventana es relleno para que la semana se
                  // lea entera: no recibe una tarjeta que nadie vería caer.
                  onDragOver={event => dentro && event.preventDefault()}
                  onDrop={() => dentro && void drop(date)}
                  onClick={() => entries.length > 0 && setSelected(date)}
                  aria-current={date === abierto ? 'date' : undefined}
                  className={cn(
                    'min-h-24 space-y-1 p-1.5 text-left align-top transition-colors',
                    dentro ? 'bg-card' : 'bg-muted text-muted-foreground',
                    dentro && dragging !== null && 'bg-info-surface',
                    date === abierto && 'ring-2 ring-ring ring-inset'
                  )}
                >
                  <span className="block text-xs font-medium text-muted-foreground">
                    {dayNumber(date)}
                  </span>
                  {entries.slice(0, PER_DAY).map(entry => (
                    <span
                      key={entry.id}
                      draggable={canEdit}
                      onDragStart={() => setDragging(entry.id)}
                      onDragEnd={() => setDragging(null)}
                      className={cn(
                        'block truncate rounded border px-1 py-0.5 text-[11px]',
                        canEdit && 'cursor-grab',
                        entry.is_overdue_without_receipt
                          ? 'border-danger-border bg-danger-surface text-danger'
                          : 'border-border'
                      )}
                      title={`${entry.description} · ${money(entry.amount)}`}
                    >
                      {entry.description}
                    </span>
                  ))}
                  {entries.length > PER_DAY && (
                    <span className="block text-[11px] text-muted-foreground">
                      y {entries.length - PER_DAY} más
                    </span>
                  )}
                </button>
              </li>
            )
          })}
        </ol>

        {/* El día elegido, entero: la celda muestra qué hay, acá se opera. */}
        {abierto !== null && (
          <section className="mt-4 space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">{day(abierto)}</h3>
            <DayEntries
              date={abierto}
              entries={byDay.get(abierto) ?? []}
              expanded={expanded.has(abierto)}
              onToggle={toggleExpanded}
              acciones={acciones}
            />
          </section>
        )}
      </div>

      {/*
        En un teléfono, los días con algo uno debajo del otro (RF-41). Siete
        columnas en una pantalla angosta no se leen, y un calendario que no se
        lee no sirve para consultarlo, que es exactamente lo que H8 pide.
      */}
      {byDay.size === 0 ? (
        <p className="rounded border border-dashed p-8 text-center text-muted-foreground md:hidden">
          No vence nada en este período.
        </p>
      ) : (
        <ol aria-label="Los días con vencimientos" className="space-y-4 md:hidden">
          {conAlgo.map(date => (
            <li
              key={date}
              className="space-y-2 rounded p-1 transition-colors data-[over=true]:bg-info-surface"
              data-over={dragging !== null}
              onDragOver={event => event.preventDefault()}
              onDrop={() => void drop(date)}
            >
              <h3 className="text-sm font-medium text-muted-foreground">{day(date)}</h3>
              <DayEntries
                date={date}
                entries={byDay.get(date) ?? []}
                expanded={expanded.has(date)}
                onToggle={toggleExpanded}
                acciones={acciones}
              />
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
