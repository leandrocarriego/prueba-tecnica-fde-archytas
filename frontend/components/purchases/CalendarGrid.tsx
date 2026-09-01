'use client'

import { useMemo, useState, useSyncExternalStore } from 'react'
import { useRouter } from 'next/navigation'

import { addDueDate, editDueDate, moveDueDate, removeDueDate } from '@/app/actions/purchases'
import { Day, Money } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Input } from '@/components/ui/input'
import { Notice } from '@/components/ui/notice'
import { Empty } from '@/components/ui/state'
import { useLiveCalendar } from '@/components/purchases/useLiveCalendar'
/*
 * `day()` y `money()` se siguen usando **como string**, y por eso este archivo
 * es una de las excepciones permanentes del chequeo de `UI-04`: un `title` y un
 * `aria-label` no pueden llevar un elemento adentro. Todo lo que se ve pasa por
 * `<Day>` y `<Money>`.
 */
import { day, money } from '@/lib/format'
import {
  MOVING_INTO_THE_PAST,
  PER_DAY,
  dayNumber,
  isInWindow,
  refusalCode,
  weeksOf,
} from '@/lib/purchases/calendar'
import { paymentStateLabel } from '@/lib/purchases/labels'
import { cn } from '@/lib/utils'
import type { Calendar, DueDate } from '@/lib/purchases/types'
import { dueDateTone, invoicePaymentTone, type BadgeTone } from '@/lib/ui/tone'

/**
 * Un mes del calendario, con lo que vence cada día, con la forma de la guía
 * visual (`3e`).
 *
 * **Es una tarjeta sola**, y eso no es decoración: encabezado, leyenda, grilla y
 * la franja de lo que apura son partes de un mismo objeto, y la guía las dibuja
 * dentro del mismo borde porque se leen en ese orden y ninguna se entiende
 * suelta. Antes el encabezado era una tarjeta y la grilla flotaba abajo sin
 * borde, así que la leyenda explicaba colores que estaban afuera de ella.
 *
 * **Es una grilla del mes** (RF-01), no una lista de los días que tienen algo:
 * un día sin vencimientos existe, vacío, y verlo vacío es parte de lo que se
 * viene a mirar. Elegir un día abre su detalle debajo de la tarjeta, que es
 * donde vive la ficha entera con sus acciones — una celda de siete columnas no
 * da para un formulario, y apretarlo ahí sería empeorar las dos cosas.
 *
 * **En un teléfono no hay grilla** (RF-41): siete columnas en 390px no se leen.
 * Ahí la tarjeta muestra los días con algo, uno debajo del otro, con la ficha
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
 *
 * **Dos cosas de la guía se dibujan distinto, y las dos por una regla escrita.**
 *
 * El botón «+ Vencimiento» del diseño es naranja; acá va en tinta. `/calendario`
 * es una de las nueve pantallas donde se decide, y en ésas el naranja está
 * prohibido (`UI-05`, `RF-21`, verificado por `tests/design-system.test.ts`):
 * una pantalla de decisiones no tiene una decisión más importante que las otras.
 *
 * La franja de abajo termina en «Ver la factura» y no en «Generar recibo». Emitir
 * un recibo es una máquina de estados con su historial y su botón, y vive en la
 * factura; repetirla acá sería dibujar el mismo estado en dos lugares que pueden
 * dejar de coincidir.
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
 * Las cuatro marcas con las que la guía pinta un vencimiento, y la quinta que
 * es «todavía no pasó nada con esto».
 *
 * La leyenda y las tarjetas de la grilla salen **de este mismo objeto**. Es la
 * diferencia entre una leyenda que explica los colores y una leyenda que se
 * escribió una vez al lado de unos colores que después cambiaron: acá, agregar
 * una marca sin agregarla a la leyenda no se puede.
 */
type Marca = 'con-recibo' | 'sin-recibo' | 'reprogramado' | 'pagado' | 'pendiente'

const MARCAS: Record<Marca, { label: string; punto: string; chip: string }> = {
  'con-recibo': {
    label: 'Con recibo',
    punto: 'bg-ok',
    chip: 'border-l-ok bg-ok-surface text-ok',
  },
  'sin-recibo': {
    label: 'Sin recibo',
    punto: 'bg-destructive',
    chip: 'border-l-destructive bg-danger-surface text-danger',
  },
  reprogramado: {
    label: 'Reprogramado',
    punto: 'bg-info',
    chip: 'border-l-info bg-info-surface text-info',
  },
  pagado: {
    label: 'Pagada',
    punto: 'bg-muted-ink',
    chip: 'border-l-muted-ink bg-muted text-muted-foreground',
  },
  // No está en la leyenda: no es un estado, es la ausencia de los cuatro.
  pendiente: {
    label: 'Sin novedad',
    punto: 'bg-border',
    chip: 'border-l-border bg-card text-foreground',
  },
}

/** Las cuatro que la guía explica, en el orden en que las explica. */
const LEYENDA: Marca[] = ['con-recibo', 'sin-recibo', 'reprogramado', 'pagado']

/**
 * De qué color va un vencimiento en la grilla.
 *
 * Están en orden de quién tapa a quién, y el orden es el de la urgencia: lo que
 * venció sin recibo es lo único que pide algo, así que gana siempre; después el
 * recibo emitido, que es el final feliz; después lo saldado, que ya no es tema;
 * y recién ahí «se movió de fecha», que es historia y no estado.
 */
function marcaDe(entry: DueDate): Marca {
  if (entry.is_overdue_without_receipt) return 'sin-recibo'
  if (entry.receipt_issued) return 'con-recibo'
  if (entry.payment_state === 'SALDADA') return 'pagado'
  if (entry.was_rescheduled) return 'reprogramado'
  return 'pendiente'
}

/**
 * En qué estado está un vencimiento, dicho con píldoras (`UI-03`).
 *
 * Antes esto era una frase corrida de fragmentos pegados con « · », donde el
 * estado de pago salía crudo del enum —«sin_pagos», con guión bajo— y lo que
 * requiere una decisión pesaba lo mismo que lo que no. Son estados de un dato,
 * así que van en la píldora.
 *
 * **El color se gana.** `venció sin recibo` tapa a `recibo emitido` porque son
 * excluyentes y el primero es el que pide algo, y `ya pasó` sólo aparece cuando
 * no hay ya una píldora roja diciendo lo mismo más fuerte.
 */
function estadosDe(entry: DueDate): ReadonlyArray<{ label: string; tone: BadgeTone }> {
  const pills: Array<{ label: string; tone: BadgeTone }> = []
  /*
   * Los dos tonos salen de `lib/ui/tone.ts` y no de una tabla propia de esta
   * pantalla: es lo que hace que «venció sin recibo» sea la **misma** píldora
   * roja acá, en `/facturas` y en la ficha del proveedor (`RF-06`).
   */
  const estado = dueDateTone(entry)
  if (estado !== null) pills.push(estado)
  if (entry.payment_state) {
    pills.push({
      label: paymentStateLabel(entry.payment_state),
      tone: invoicePaymentTone(entry.payment_state),
    })
  }
  return pills
}

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
  setOver: (date: string | null) => void
  run: (action: () => Promise<{ ok: boolean; message?: string }>) => Promise<boolean>
  move: (entry: DueDate, next: string, reason: string | null) => Promise<void>
}

/** Una movida planteada y todavía sin contestar (RF-25). */
interface Movida {
  entry: DueDate
  next: string
  reason: string | null
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
      {/*
        Abrir el día no cambia ningún dato: sólo muestra lo que ya está, así que
        puede ir en el azul de enlace sin violar `RF-13`.
      */}
      {entries.length > PER_DAY && (
        <Button type="button" variant="link" size="sm" onClick={() => onToggle(date)}>
          {expanded ? 'Ver menos' : `y ${entries.length - PER_DAY} más en este día`}
        </Button>
      )}
    </>
  )
}

/** Una tarjeta entera, con todo lo que la spec pide leer de un vencimiento. */
function DueDateCard({ entry, acciones }: { entry: DueDate; acciones: Acciones }) {
  const { canEdit, busy, moving, editing, setMoving, setEditing, setDragging, setOver, run, move } =
    acciones
  const estados = estadosDe(entry)
  return (
    <li
      draggable={canEdit && !busy}
      onDragStart={() => setDragging(entry.id)}
      onDragEnd={() => {
        setDragging(null)
        setOver(null)
      }}
      className={cn(
        'rounded-lg border border-border p-3 text-sm',
        canEdit && 'cursor-grab',
        entry.is_overdue_without_receipt && 'border-danger-border bg-danger-surface'
      )}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-medium">{entry.description}</span>
        {/* `UI-04`: la plata en mono tabular, que es lo que deja leer una columna. */}
        <Money value={entry.amount} />
      </div>
      {estados.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {estados.map(estado => (
            <Badge key={estado.label} tone={estado.tone}>
              {estado.label}
            </Badge>
          ))}
        </div>
      )}
      <p className="mt-1.5 text-xs text-muted-foreground">
        {/* De dónde salió y quién lo cargó: procedencia, no estado. */}
        {/* RF-02: el proveedor, cuando el vencimiento tiene uno. */}
        {entry.supplier_name && `${entry.supplier_name} · `}
        {entry.origin === 'INVOICE' ? 'De una factura' : 'Cargado a mano'}
        {entry.was_rescheduled && (
          <>
            {' · reprogramado, original '}
            <Day value={entry.original_date} />
          </>
        )}
        {entry.created_by_name && (
          <>
            {` · lo cargó ${entry.created_by_name}`}
            {entry.created_at && (
              <>
                {' el '}
                <Day value={entry.created_at} />
              </>
            )}
          </>
        )}
      </p>
      {(entry.changes ?? []).length > 0 && (
        <ul className="mt-1 text-xs text-muted-foreground">
          {(entry.changes ?? []).map(change => (
            <li key={change.id}>
              <Day value={change.previous_date} /> → <Day value={change.new_date} />
              {change.actor_name ? ` · lo movió ${change.actor_name}` : ''}
              {change.reason ? ` · ${change.reason}` : ''}
            </li>
          ))}
        </ul>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {entry.invoice_id && (
          <a className="text-xs text-link hover:underline" href={`/facturas/${entry.invoice_id}`}>
            Ver la factura
          </a>
        )}
        {canEdit && (
          <>
            <Button
              type="button"
              variant="outline"
              size="sm"
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
                  size="sm"
                  disabled={busy}
                  onClick={() => setEditing(editing === entry.id ? null : entry.id)}
                >
                  Corregir
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
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

export function CalendarGrid({
  calendar,
  canEdit,
  viewerId = null,
}: {
  calendar: Calendar
  canEdit: boolean
  /**
   * Quién está mirando, para no contarse a sí mismo entre los presentes.
   *
   * Opcional porque la grilla se puede dibujar sin sesión —una vista previa,
   * un render suelto— y entonces no hay un «yo» del que distinguir a los
   * demás. Sin canal en vivo no hay presencias, así que no se nota.
   */
  viewerId?: number | null
}) {
  const router = useRouter()
  // Se anuncia quien puede cambiar algo: ver quién está es de los tres roles,
  // aparecer en la lista es de los dos que pueden mover un vencimiento.
  const { state: live, lastChange, viewers } = useLiveCalendar({ announce: canEdit })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [agregando, setAgregando] = useState(false)
  const [onDate, setOnDate] = useState('')
  const [description, setDescription] = useState('')
  const [amount, setAmount] = useState('')
  // Qué entrada se está moviendo o corrigiendo, y cuál se está arrastrando.
  const [moving, setMoving] = useState<number | null>(null)
  const [editing, setEditing] = useState<number | null>(null)
  const [dragging, setDragging] = useState<number | null>(null)
  // El día sobre el que está la tarjeta ahora mismo. Antes se pintaban los
  // treinta a la vez, que dice «se puede soltar» pero no dice dónde.
  const [over, setOver] = useState<string | null>(null)
  /*
   * La movida que espera una respuesta (RF-25). Es estado y no una llamada que
   * devuelve `true`, porque preguntar dejó de ser sincrónico: el `window.confirm`
   * que había acá congelaba el hilo, no se podía leer entero, y algunos
   * navegadores lo saltean devolviendo `false` — o sea, contestando «no» en
   * nombre de una persona a la que nunca se le preguntó.
   */
  const [preguntando, setPreguntando] = useState<Movida | null>(null)
  // Los días que la persona pidió ver enteros (RF-08).
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  /*
   * Hoy, y por qué llega después del primer dibujo.
   *
   * Esta grilla la renderiza primero el servidor, que está en UTC, y después el
   * navegador, que está donde está la persona. Calcular «hoy» durante el render
   * daría dos respuestas distintas para el mismo HTML y React lo cantaría como
   * error de hidratación. `useSyncExternalStore` es la forma de decir eso sin
   * rodeos: **en el servidor todavía no se sabe** —`null`— y en el navegador es
   * el día de quien mira. Lo único que se nota es que el recuadro de HOY aparece
   * un instante después, que nadie percibe.
   */
  const hoy = useSyncExternalStore(elRelojNoAvisa, hoyLocal, noSeSabeTodavia)

  const byDay = new Map<string, DueDate[]>()
  for (const entry of calendar.items) {
    byDay.set(entry.on_date, [...(byDay.get(entry.on_date) ?? []), entry])
  }
  const conAlgo = [...byDay.keys()].sort()

  // El día abierto en la grilla. Arranca en el primero que tenga algo, para que
  // la pantalla llegue con detalle en vez de con una invitación a hacer clic.
  const [selected, setSelected] = useState<string | null>(conAlgo[0] ?? null)
  /*
   * Un día **vacío también se abre**: en un calendario «acá no vence nada» es
   * información, y es la mitad de por qué RF-01 pide una grilla y no una lista.
   * Antes sólo se podían elegir los días con algo, así que la grilla dejaba
   * treinta botones que no hacían nada en el orden de tabulación. Si el mes
   * cambia y el día elegido se fue de la ventana, se vuelve al primero con algo.
   */
  const abierto =
    selected !== null && isInWindow(selected, calendar.since, calendar.until)
      ? selected
      : (conAlgo[0] ?? null)

  /**
   * Lo que más apura de esta ventana, que es lo que la guía pone en la franja.
   *
   * Primero lo que ya venció sin recibo —eso no espera— y después lo primero
   * que vence y todavía no lo tiene. Lo saldado no entra: una factura pagada no
   * apura aunque no tenga recibo emitido todavía.
   *
   * Devuelve `null` cuando no hay nada, y entonces **la franja no se dibuja**.
   * Una franja de urgencias que dice «no hay urgencias» ocupa el mismo lugar
   * todos los días y enseña a no mirarla.
   */
  const urgente = useMemo(() => {
    const porFecha = (a: DueDate, b: DueDate) => a.on_date.localeCompare(b.on_date)
    const sinRecibo = calendar.items.filter(
      entry => !entry.receipt_issued && entry.payment_state !== 'SALDADA'
    )
    const vencidos = sinRecibo.filter(entry => entry.is_overdue_without_receipt).sort(porFecha)
    if (vencidos.length > 0) return vencidos[0]
    if (hoy === null) return null
    const proximos = sinRecibo.filter(entry => entry.on_date >= hoy).sort(porFecha)
    return proximos[0] ?? null
  }, [calendar.items, hoy])

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
    // El primer intento también pasa por el guard: sin esto el botón «Mover»
    // seguía habilitado y la tarjeta arrastrable durante todo el viaje, y
    // soltarla dos veces rápido mandaba dos `PUT`.
    if (busy) return
    setBusy(true)
    setError(null)
    const first = await moveDueDate(entry.id, next, reason)
    setBusy(false)
    if (first.ok) {
      setMoving(null)
      router.refresh()
      return
    }
    if (refusalCode(first) === MOVING_INTO_THE_PAST) {
      // RF-25: se pregunta antes, y la respuesta vuelve como confirmación.
      setPreguntando({ entry, next, reason })
      return
    }
    setError(first.message)
  }

  /** Que sí: se repite la movida, ahora con la confirmación puesta (RF-25). */
  async function confirmarLaMovida() {
    if (preguntando === null) return
    const { entry, next, reason } = preguntando
    setPreguntando(null)
    if (await run(() => moveDueDate(entry.id, next, reason, true))) setMoving(null)
  }

  /** Soltar una tarjeta sobre un día es moverla a ese día (RF-19). */
  async function drop(date: string) {
    const entry = calendar.items.find(item => item.id === dragging)
    setDragging(null)
    setOver(null)
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
    setOver,
    run,
    move,
  }

  const cambio =
    lastChange === null
      ? null
      : `${lastChange.actorName || 'Alguien'} ${VERBOS[lastChange.action] ?? 'cambió'} un vencimiento`

  // Los demás, no uno mismo: el canal devuelve también el propio anuncio, y
  // dibujarse a sí mismo entre «los que también están mirando» es raro de leer.
  const otros = viewers.filter(one => one.id !== viewerId)

  const semanas = weeksOf(calendar.since, calendar.until)

  return (
    <div className="space-y-4">
      {/*
        RF-25: mover algo a una fecha que ya pasó se pregunta antes, y la
        respuesta vuelve al backend como confirmación. Cerrar por `Escape` o por
        el fondo es decir que no: la única forma de seguir es el botón.
      */}
      <ConfirmDialog
        open={preguntando !== null}
        tone="warn"
        title="La fecha nueva ya pasó"
        confirmLabel="Moverlo igual"
        busy={busy}
        onConfirm={() => void confirmarLaMovida()}
        onCancel={() => setPreguntando(null)}
      >
        {preguntando !== null && (
          <>
            Estás por mover «{preguntando.entry.description}» al <Day value={preguntando.next} />,
            que ya pasó. Queda registrado quién lo movió y desde qué fecha.
          </>
        )}
      </ConfirmDialog>

      {/*
        Los avisos van **arriba de la tarjeta que califican** (`RF-14`), y no
        adentro: lo que dicen es sobre todo el calendario, no sobre una parte.

        Que el canal se corte no es un error de la persona ni algo que pueda
        arreglar: lo que necesita saber es que lo que está mirando puede haber
        quedado viejo, porque sobre esta pantalla se toman decisiones entre dos.
      */}
      {live === 'caido' && (
        <Notice tone="warn" title="Se cortó la conexión en vivo">
          Lo que ves puede estar desactualizado. Se está reintentando solo.
        </Notice>
      )}

      {live === 'en-vivo' && cambio !== null && (
        <Notice tone="info" title={cambio}>
          La pantalla ya se actualizó.
        </Notice>
      )}

      {error && (
        <Notice tone="danger" title="No se pudo guardar">
          {error}
        </Notice>
      )}

      {/*
        `TS-08`: mientras la escritura viaja, la pantalla lo dice. Antes sólo
        deshabilitaba botones, y una pantalla que se congela sin explicar por
        qué se lee como una pantalla rota.
      */}
      {busy && (
        <p role="status" className="text-sm text-muted-foreground">
          Guardando…
        </p>
      )}

      {/* La tarjeta del mes, entera, como la dibuja la guía (`3e`). */}
      <section className="overflow-hidden rounded-xl border border-border bg-card">
        {/*
          El encabezado: el mes, que la pantalla se actualiza sola, quién más la
          está mirando y la única acción que el calendario tiene propia. Las
          cuatro cosas arriba porque las cuatro califican todo lo que viene abajo.
        */}
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border px-6 py-4">
          <div className="space-y-0.5">
            <h2 className="text-xl font-semibold tracking-tight text-foreground">
              {tituloDelMes(calendar.since)}
            </h2>
            <p className="text-[13px] text-muted-foreground">
              {live === 'en-vivo'
                ? 'Se actualiza en vivo'
                : live === 'conectando'
                  ? 'Conectando…'
                  : 'Sin conexión en vivo'}
              {otros.length > 0 && ` · ${frasePresentes(otros)}`}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Avatares viewers={otros} />
            {canEdit && (
              /*
                En tinta y no en naranja: `/calendario` es pantalla de decisión y
                ahí el naranja está prohibido (`RF-21`). La guía lo dibuja
                naranja; la regla es posterior y gana.
              */
              <Button
                type="button"
                aria-expanded={agregando}
                onClick={() => setAgregando(current => !current)}
              >
                {agregando ? 'Cancelar' : '+ Vencimiento'}
              </Button>
            )}
          </div>
        </header>

        {/* Qué quiere decir cada color, arriba de los colores que explica. */}
        <ul className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-border px-6 py-3">
          {LEYENDA.map(marca => (
            <li
              key={marca}
              className="flex items-center gap-1.5 text-[11.5px] text-muted-foreground"
            >
              <span aria-hidden className={cn('size-2.5 rounded-sm', MARCAS[marca].punto)} />
              {MARCAS[marca].label}
            </li>
          ))}
        </ul>

        {/*
          Cargar algo a mano (RF-12). Se despliega desde el encabezado en lugar
          de vivir siempre abierto al pie: el calendario se abre para mirar, y un
          formulario permanente debajo de la grilla decía lo contrario.
        */}
        {canEdit && agregando && (
          <form
            className="flex flex-wrap items-end gap-3 border-b border-border bg-muted px-6 py-4"
            onSubmit={event => {
              event.preventDefault()
              void run(() => addDueDate(onDate, description, amount || null)).then(ok => {
                if (ok) {
                  setOnDate('')
                  setDescription('')
                  setAmount('')
                  setAgregando(false)
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

        {/*
          La grilla del mes, desde una pantalla ancha. Cada día es una celda —haya
          o no algo ese día— y soltar una tarjeta sobre una celda la mueve a ese
          día, que es RF-19 dicho en la forma en que un calendario lo dice.
        */}
        <div className="hidden md:block">
          <div className="grid grid-cols-7 border-b border-border bg-muted">
            {DIAS.map(nombre => (
              <span key={nombre} className="section-label py-2.5 text-center">
                {nombre}
              </span>
            ))}
          </div>
          {/*
            Las líneas de la grilla son el fondo asomando por las juntas, no un
            borde por celda: así ninguna se duplica contra la de al lado ni contra
            el borde de la tarjeta.
          */}
          <ol aria-label="El mes, día por día" className="grid grid-cols-7 gap-px bg-border">
            {semanas.flat().map((date, index) => {
              const entries = byDay.get(date) ?? []
              const dentro = isInWindow(date, calendar.since, calendar.until)
              // Lunes a domingo: las dos últimas de cada semana son el fin de
              // semana, y van apagadas porque el negocio no factura esos días.
              const finDeSemana = index % 7 >= 5
              const esHoy = date === hoy
              return (
                <li key={date} className="contents">
                  <button
                    type="button"
                    // Un día fuera de la ventana es relleno para que la semana se
                    // lea entera: no recibe una tarjeta que nadie vería caer.
                    onDragOver={event => {
                      if (!dentro) return
                      event.preventDefault()
                      setOver(date)
                    }}
                    onDragLeave={() => setOver(current => (current === date ? null : current))}
                    onDrop={() => dentro && void drop(date)}
                    onClick={() => dentro && setSelected(date)}
                    aria-current={date === abierto ? 'date' : undefined}
                    aria-label={`${day(date)}, ${
                      entries.length === 0
                        ? 'no vence nada'
                        : `${entries.length} ${entries.length === 1 ? 'vencimiento' : 'vencimientos'}`
                    }`}
                    className={cn(
                      'min-h-20 space-y-1 p-2 text-left align-top transition-colors',
                      // Tres fondos y tres cosas distintas: el mes, su fin de
                      // semana, y los días de al lado que están para que la
                      // semana se lea entera. `cn` resuelve el conflicto de
                      // `bg-*` a favor del último, así que el orden es la regla.
                      dentro ? 'bg-card' : 'bg-secondary',
                      dentro && finDeSemana && 'bg-background',
                      // Sólo el día bajo la tarjeta, no los treinta a la vez.
                      dentro && over === date && 'bg-info-surface',
                      esHoy && date !== abierto && 'ring-1 ring-foreground ring-inset',
                      date === abierto && 'ring-2 ring-ring ring-inset'
                    )}
                  >
                    <span
                      className={cn(
                        'amount block text-[11px]',
                        esHoy
                          ? 'font-semibold text-foreground'
                          : dentro
                            ? 'font-medium text-muted-ink'
                            : 'font-medium text-muted-ink/60'
                      )}
                    >
                      {dayNumber(date)}
                      {esHoy && ' · HOY'}
                    </span>
                    {entries.slice(0, PER_DAY).map(entry => (
                      <span
                        key={entry.id}
                        draggable={canEdit && !busy}
                        onDragStart={() => setDragging(entry.id)}
                        onDragEnd={() => {
                          setDragging(null)
                          setOver(null)
                        }}
                        className={cn(
                          'block truncate rounded-r border-l-2 px-1.5 py-1 text-[11px] font-semibold',
                          canEdit && 'cursor-grab',
                          MARCAS[marcaDe(entry)].chip
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
        </div>

        {/*
          En un teléfono, los días con algo uno debajo del otro (RF-41). Siete
          columnas en una pantalla angosta no se leen, y un calendario que no se
          lee no sirve para consultarlo, que es exactamente lo que H8 pide.
        */}
        <div className="md:hidden">
          {byDay.size === 0 ? (
            <div className="px-6 py-6">
              <Empty title="No vence nada en este período." />
            </div>
          ) : (
            <ol aria-label="Los días con vencimientos" className="divide-y divide-border">
              {conAlgo.map(date => (
                <li
                  key={date}
                  className="space-y-2 px-4 py-4 transition-colors data-[over=true]:bg-info-surface"
                  data-over={over === date}
                  onDragOver={event => {
                    event.preventDefault()
                    setOver(date)
                  }}
                  onDragLeave={() => setOver(current => (current === date ? null : current))}
                  onDrop={() => void drop(date)}
                >
                  <Day
                    value={date}
                    as="div"
                    className="text-sm font-medium text-muted-foreground"
                  />
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
        </div>

        {/* La franja de la guía: lo único que apura, dicho como una frase. */}
        {urgente && (
          <div className="flex flex-wrap items-center gap-3 border-t border-border bg-warn-surface px-6 py-4">
            <div className="min-w-0 flex-1 space-y-0.5">
              <p className="text-[13px] font-semibold text-foreground">{urgencia(urgente, hoy)}</p>
              <p className="text-xs text-warn">
                {urgente.supplier_name && `${urgente.supplier_name} · `}
                {urgente.amount !== null && (
                  <>
                    <Money value={urgente.amount} as="span" />
                    {' · '}
                  </>
                )}
                vence <Day value={urgente.on_date} />
                {urgente.payment_state && ` · ${paymentStateLabel(urgente.payment_state)}`}
              </p>
            </div>
            {canEdit && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setSelected(urgente.on_date)
                  setMoving(urgente.id)
                }}
              >
                Mover
              </Button>
            )}
            {urgente.invoice_id && (
              <Button asChild variant="outline" size="sm">
                <a href={`/facturas/${urgente.invoice_id}`}>Ver la factura</a>
              </Button>
            )}
          </div>
        )}
      </section>

      {/*
        El día elegido, entero: la celda muestra qué hay, acá se opera. Va abajo
        de la tarjeta y no adentro porque adentro rompería la grilla en dos, y
        porque en el teléfono la lista ya trae la ficha entera.
      */}
      {abierto !== null && (
        <section className="hidden space-y-2 md:block">
          <Day value={abierto} as="div" className="text-sm font-medium text-muted-foreground" />
          {(byDay.get(abierto) ?? []).length === 0 ? (
            <Empty title="No vence nada este día." />
          ) : (
            <DayEntries
              date={abierto}
              entries={byDay.get(abierto) ?? []}
              expanded={expanded.has(abierto)}
              onToggle={toggleExpanded}
              acciones={acciones}
            />
          )}
        </section>
      )}
    </div>
  )
}

/** Los meses, escritos, para titular la ventana sin depender de la zona horaria. */
const MESES = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
]

/**
 * El mes de una ventana, leído del texto de la fecha y no de un `Date`.
 *
 * `2026-08-01` construido como `Date` en un navegador al oeste de Greenwich es
 * el 31 de julio, y el calendario se titularía con el mes anterior al que está
 * mostrando. Partir el string no tiene ese problema porque no hay ninguna zona
 * horaria de por medio.
 */
function tituloDelMes(iso: string): string {
  const [year, month] = iso.split('-')
  const index = Number(month) - 1
  return index >= 0 && index < MESES.length ? `${MESES[index]} ${year}` : iso
}

/**
 * Las dos mitades que `useSyncExternalStore` pide además del valor.
 *
 * No hay a qué suscribirse: nadie deja el calendario abierto cruzando la
 * medianoche esperando que la celda de HOY se corra sola, y un temporizador
 * puesto por las dudas sería trabajo permanente para un caso que no existe. Y
 * en el servidor la respuesta honesta es «todavía no se sabe», no la fecha de
 * un servidor que está en otro huso que quien va a leer la pantalla.
 */
const elRelojNoAvisa = () => () => {}
const noSeSabeTodavia = () => null

/** Hoy, en la zona de quien mira, escrito como las fechas del calendario. */
function hoyLocal(): string {
  const now = new Date()
  const mes = String(now.getMonth() + 1).padStart(2, '0')
  const dia = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${mes}-${dia}`
}

/** Cuántos días hay entre dos fechas ISO, sin que ningún huso las corra. */
function diasEntre(desde: string, hasta: string): number {
  const utc = (iso: string) =>
    Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)))
  return Math.round((utc(hasta) - utc(desde)) / 86_400_000)
}

/**
 * La frase de la franja: qué es lo que apura, en una línea.
 *
 * Sin `hoy` —el primer dibujo, antes de montar— no se cuentan días: se dice qué
 * es y que no tiene recibo, que es lo verdadero en cualquier momento.
 */
function urgencia(entry: DueDate, hoy: string | null): string {
  const que = entry.description
  if (entry.is_overdue_without_receipt) return `${que} venció y todavía no tiene recibo`
  if (hoy === null) return `${que} todavía no tiene recibo`
  const dias = diasEntre(hoy, entry.on_date)
  if (dias <= 0) return `${que} vence hoy y todavía no tiene recibo`
  if (dias === 1) return `${que} vence mañana y todavía no tiene recibo`
  return `${que} vence en ${dias} días y todavía no tiene recibo`
}

/** Las iniciales con las que se dibuja a una persona presente. */
function iniciales(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(part => part[0]?.toUpperCase() ?? '')
      .join('') || '?'
  )
}

/**
 * Quiénes están mirando esta pantalla, además de uno mismo (H5 de 006).
 *
 * Los círculos van en el encabezado, arriba a la derecha, y la frase que los
 * explica va en el subtítulo. **Las dos cosas, no una**: un par de iniciales en
 * un rincón no dice nada a quien no sabe qué significan, y una frase sola no
 * deja ver de un vistazo cuántos son. Con nadie del otro lado no se dibuja
 * ninguna: un «sos el único mirando» permanente es ruido sobre una pantalla de
 * trabajo.
 */
function Avatares({ viewers }: { viewers: { id: number; name: string }[] }) {
  if (viewers.length === 0) return null
  return (
    <span className="flex -space-x-2">
      {viewers.map(one => (
        <span
          key={one.id}
          title={one.name}
          className="flex size-7 items-center justify-center rounded-full border-2 border-card bg-primary text-[10px] font-semibold text-primary-foreground"
        >
          {iniciales(one.name)}
        </span>
      ))}
    </span>
  )
}

/** La otra mitad de los círculos: quiénes son, dicho con nombres. */
function frasePresentes(viewers: { name: string }[]): string {
  const nombres = viewers.map(one => one.name.split(' ')[0] || 'Alguien')
  if (nombres.length === 1) return `${nombres[0]} también está viendo esta pantalla`
  return `${nombres.slice(0, -1).join(', ')} y ${nombres.at(-1)} también están viendo esta pantalla`
}
