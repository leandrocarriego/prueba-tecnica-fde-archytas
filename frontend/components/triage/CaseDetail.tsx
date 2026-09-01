'use client'

import { Fragment, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

import { resolveCase } from '@/app/actions/triage'
import { Code } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input, selectClassName } from '@/components/ui/input'
import { Notice } from '@/components/ui/notice'
import { useToast } from '@/components/ui/toast'
import { formatDay, formatMoment, formatPrice } from '@/lib/catalog/format'
import type { Category } from '@/lib/catalog/types'
import type { Supplier } from '@/lib/purchases/types'
import {
  ACKNOWLEDGE_ONLY_KINDS,
  DISPUTED_KINDS,
  LOADABLE_KINDS,
  caseKindLabel,
  sectionLabel,
  type Case,
} from '@/lib/triage/types'

interface CaseDetailProps {
  item: Case
  /**
   * Whether this person may change a correction, which is a different question
   * from whether they may empty this queue. Resolving a case is `PRICES` in
   * writing — the owner and purchasing; correcting a value is `PRODUCT_CATALOG`
   * in writing — the owner and sales. So purchasing reaches this screen and
   * cannot take that door, and offering it anyway would be a link that answers
   * 403. Whoever cannot take it is told who can, rather than left in front of
   * an instruction with nobody attached to it.
   */
  mayCorrect: boolean
  /**
   * Los rubros con los que se resuelve un caso `unknown_category` (RF-14 de
   * 010). Los pasa la pantalla: este panel es de `triage` y pedirlos él mismo
   * lo ataría al catálogo, que es de otro módulo y de otro dominio.
   */
  categories: Category[]
  /**
   * El padrón, para cargar a mano la factura o la orden que el portal publicó
   * rota (RF de la carga manual). Lo pasa la pantalla por la misma razón que
   * los rubros: este panel es de `triage`, y pedirlo él mismo lo ataría a
   * compras.
   *
   * Vacío cuando quien mira no alcanza el padrón, y entonces la carga a mano no
   * se ofrece: sin proveedor no hay factura que registrar, y un formulario que
   * termina en un 403 es peor que no ofrecerlo.
   */
  suppliers: Supplier[]
}

function payloadText(item: Case, key: string): string {
  const value = item.payload[key]
  return typeof value === 'string' || typeof value === 'number' ? String(value) : ''
}

/** The correction a refusal is about: where to look at it, and who made it. */
interface RefusedByCorrection {
  productId: number
  correctedBy: string | null
}

/**
 * That correction, when the refusal was about one.
 *
 * Hung on `correction_id`, which only this refusal carries, and not on
 * `product_id`, which several carry. Deciding by the product would light the
 * links up under refusals that have nothing to do with a correction — a
 * `missing_product` case whose product a revoked rule removed answers 404 with
 * a `product_id` in it, and the panel would offer «Ver la corrección» for a
 * correction that does not exist, on a page that answers 404 too.
 *
 * `details` is whatever the backend put in the envelope, so every key is asked
 * rather than trusted. A refusal with nothing in it — the session expired, the
 * API did not answer — leaves the message on its own, which is still the whole
 * of what RF-22 asks for.
 */
function refusedByCorrection(
  details: Record<string, unknown> | undefined
): RefusedByCorrection | null {
  if (typeof details?.correction_id !== 'number') return null
  const productId = details.product_id
  if (typeof productId !== 'number') return null
  const correctedBy = details.corrected_by_name
  return { productId, correctedBy: typeof correctedBy === 'string' ? correctedBy : null }
}

/** Un dato del caso: su rótulo y su valor, tal como el paso 1 lo dibuja. */
interface Field {
  label: string
  value: ReactNode
  /** Ocupa las dos columnas: lo que se lee como bloque, no como valor. */
  wide?: boolean
}

/**
 * Lo que el caso trae, del portal y de la lectura que lo apartó (RF-11).
 *
 * Es lo que evita que resolver un pendiente empiece por salir a buscar el dato.
 * Cada campo se dibuja **si vino**: los pendientes abiertos antes de la 011 no
 * tienen origen ni hora de lectura en su `payload` y nadie se los va a inventar
 * hacia atrás, y un rubro que volvió a la cola porque alguien revocó su regla
 * no salió de ninguna lectura, así que no dice cuándo se leyó.
 */
function fieldsOf(item: Case): Field[] {
  const fields: Field[] = []
  const add = (key: string, label: string, render: (text: string) => ReactNode): void => {
    const text = payloadText(item, key)
    if (text) fields.push({ label, value: render(text) })
  }

  add('product_code', 'Código', text => <Code value={text} />)
  add('description', 'Descripción', text => text)
  add('price', 'Precio que trajo la lista', text => (
    <span className="amount">{formatPrice(text)}</span>
  ))
  add('category_text', 'Forma escrita', text => <Code value={text} />)
  add('origin', 'Salió de', text => text)
  add('read_at', 'Se leyó', text => <span className="amount">{formatMoment(text)}</span>)

  const excerpt = payloadText(item, 'excerpt')
  if (excerpt) {
    fields.push({
      label: 'Lo que decía la fila',
      wide: true,
      value: (
        <pre className="overflow-x-auto rounded-md border border-border bg-card p-2.5 font-mono text-xs">
          {excerpt}
        </pre>
      ),
    })
  }

  return fields
}

/** Una de las decisiones que la clase de caso admite, como tarjeta elegible. */
interface Choice {
  id: string
  /** El rótulo mono de la tarjeta, como «QUEDA ESTE» en la guía visual. */
  overline: string
  title: string
  /** Qué pasa si se elige. Es lo que el paso 3 repite antes de confirmar. */
  detail: string
  decision: Record<string, unknown>
}

/**
 * Las decisiones que se eligen como tarjeta, por clase de caso.
 *
 * Las dos clases que faltan acá no se eligen: se escriben. Un precio ilegible
 * necesita el número que la fila no dejó leer, y una forma escrita sin rubro
 * necesita el rubro — y son cien, no dos, así que van en un `select` y no en
 * tarjetas.
 */
function choicesOf(item: Case): Choice[] {
  switch (item.kind) {
    case 'unknown_product':
      return [
        {
          id: 'incorporate',
          overline: 'ENTRA',
          title: 'Incorporarlo al catálogo',
          detail: 'Queda como producto vigente, con el precio que trajo la lista.',
          decision: { action: 'incorporate' },
        },
        {
          id: 'ignore',
          overline: 'QUEDA FUERA',
          title: 'Dejarlo fuera',
          detail: 'No entra al catálogo, y si vuelve a llegar no se vuelve a preguntar.',
          decision: { action: 'ignore' },
        },
      ]
    case 'missing_product':
      return [
        {
          id: 'discontinue',
          overline: 'DISCONTINUADO',
          title: 'Darlo por discontinuado',
          detail: 'Deja de figurar como vigente. Se conserva el último precio conocido.',
          decision: { action: 'discontinue' },
        },
        {
          id: 'keep',
          overline: 'SIGUE VIGENTE',
          title: 'Mantenerlo vigente',
          detail: 'Sigue en el catálogo aunque esta lista no lo haya traído.',
          decision: { action: 'keep' },
        },
      ]
    case 'unreadable_history':
      return [
        {
          id: 'ignore',
          overline: 'REVISADO',
          title: 'Dar el historial por revisado',
          detail: 'El historial no se reconstruye desde acá: el origen es de sólo lectura.',
          decision: { action: 'ignore' },
        },
      ]
    case 'unreadable_invoice_row':
    case 'unreadable_order_row':
      /*
        Las dos salidas de una fila que el portal publicó rota, y las dos son
        respuestas de verdad. Cargarla a mano mete el dato que si no no entra a
        ningún total; darla por revisada es lo honesto cuando el papel no está.
      */
      return [
        {
          id: 'load',
          overline: 'SE CARGA',
          title: 'Cargarla a mano',
          detail:
            item.kind === 'unreadable_invoice_row'
              ? 'La escribís vos, mirando el papel: entra al catálogo de facturas y al calendario.'
              : 'La escribís vos, mirando el papel: entra al listado de órdenes.',
          decision: { action: 'load' },
        },
        {
          id: 'ignore',
          overline: 'REVISADO',
          title: 'Darlo por revisado',
          detail: 'No entra ningún dato: queda constancia de que alguien lo miró.',
          decision: { action: 'ignore' },
        },
      ]
    case 'disputed_invoice':
    case 'disputed_order':
      /*
        Los dos valores, uno al lado del otro, que es la única forma de contestar
        esta pregunta. Ninguno de los dos está elegido de antemano: el portal es
        la autoridad sobre lo que publica, y la persona vio el papel.
      */
      return [
        {
          id: 'portal',
          overline: 'LO DEL PORTAL',
          title: 'Queda lo que publicó el portal',
          detail: describeValues(item.payload.published),
          decision: { keep: 'portal' },
        },
        {
          id: 'manual',
          overline: 'LO CARGADO',
          title: 'Queda lo que se cargó a mano',
          detail: describeValues(item.payload.typed),
          decision: { keep: 'manual' },
        },
      ]
    default:
      if (!ACKNOWLEDGE_ONLY_KINDS.includes(item.kind)) return []
      return [
        {
          id: 'ignore',
          overline: 'REVISADO',
          title: 'Darlo por revisado',
          detail: 'No cambia ningún dato: deja constancia de que alguien lo miró.',
          decision: { action: 'ignore' },
        },
      ]
  }
}

/**
 * Los valores de un lado de la discusión, escritos para que se comparen de un
 * vistazo.
 *
 * Vienen del caso tal como los dejó quien abrió la discusión —fechas ISO,
 * importes sin formatear— y se formatean acá, que es donde los lee una persona.
 * Una clave que no se reconoce se muestra igual: es un dato del caso, y
 * esconderlo sería decidir por quien mira.
 */
function describeValues(values: unknown): string {
  if (typeof values !== 'object' || values === null) return 'Sin datos.'
  return Object.entries(values as Record<string, unknown>)
    .map(([key, value]) => {
      const text = String(value)
      if (key === 'fecha') return formatDay(text)
      if (key === 'total' || key === 'importe') return text === '—' ? '—' : formatPrice(text)
      return `${key}: ${text}`
    })
    .join(' · ')
}

/** La pregunta del paso 2, que es la decisión dicha en la lengua del negocio. */
function questionOf(item: Case): string {
  switch (item.kind) {
    case 'unknown_product':
      return '¿Incorporamos este producto?'
    case 'missing_product':
      return '¿Dejó de venderse?'
    case 'unreadable_row':
      return '¿Qué precio traía la fila?'
    case 'unknown_category':
      return '¿A qué rubro va esta forma escrita?'
    case 'unreadable_history':
      return '¿Damos el historial por revisado?'
    case 'unreadable_invoice_row':
      return '¿Qué hacemos con esta fila de facturas?'
    case 'unreadable_order_row':
      return '¿Qué hacemos con esta fila de órdenes?'
    case 'disputed_invoice':
    case 'disputed_order':
      return '¿Cuál de los dos valores queda?'
    default:
      return '¿Lo damos por revisado?'
  }
}

/** Lo que se escribe para cargar una fila a mano. */
interface LoadForm {
  number: string
  date: string
  total: string
  supplierId: string
  productText: string
  quantity: string
  amount: string
}

/**
 * La factura que se está escribiendo, o `null` mientras le falte algo.
 *
 * Los cuatro campos obligatorios son los que hacen que la factura **sea** una
 * factura: sin proveedor no se le puede calcular el vencimiento ni sumarla a
 * una cuenta, y sin número, fecha o total no hay nada que registrar. El
 * vencimiento no se pide: sale del plazo acordado con el proveedor, que es de
 * dónde sale el de todas las demás.
 */
function invoiceDecision(
  form: LoadForm,
  supplier: Supplier | null
): Record<string, unknown> | null {
  if (!form.number.trim() || !form.date || !form.total || supplier === null) return null
  return {
    action: 'load',
    number: form.number.trim(),
    issued_on: form.date,
    total: form.total,
    supplier_id: supplier.id,
  }
}

/** La orden que se está escribiendo. El producto y el importe pueden faltar. */
function orderDecision(form: LoadForm, supplier: Supplier | null): Record<string, unknown> | null {
  if (!form.number.trim() || !form.date || supplier === null) return null
  return {
    action: 'load',
    number: form.number.trim(),
    ordered_on: form.date,
    supplier_id: supplier.id,
    product_text: form.productText.trim(),
    quantity: form.quantity === '' ? null : Number(form.quantity),
    amount: form.amount === '' ? null : form.amount,
  }
}

/** Una cifra del bloque «qué pasa si confirmás». */
interface Figure {
  value: string
  label: string
  /** Verde: lo que tranquiliza, como «se puede deshacer» en la guía. */
  tone?: 'ok'
}

const STEPS = ['mirar el caso', 'elegir qué hacer', 'confirmar'] as const

/**
 * El caso abierto y su asistente paso a paso (guía visual `3d`).
 *
 * Es el panel derecho de la pantalla, y son tres pasos porque la guía los
 * muestra y porque cada uno contesta algo distinto: **mirar** el dato que trajo
 * el portal, **elegir** qué hacer con él, y **confirmar** sabiendo qué se mueve.
 * El tercero es el que faltaba: hasta acá la decisión se tomaba de un clic, sin
 * que la pantalla dijera nunca cuántos productos quedaban clasificados ni que
 * lo decidido se guarda como regla.
 *
 * Ninguna cifra del paso 3 está estimada: salen del `payload` del caso —cuántos
 * productos esperaban esa forma escrita, cuántas veces llegó la misma fila— o
 * de lo que la persona acaba de escribir. Cuando el caso no trae una cifra, el
 * bloque no la inventa: dice en palabras qué va a pasar.
 *
 * **Ningún naranja acá** (`RF-21`, `UI-05`): esta es una pantalla donde se
 * decide caso por caso, y un acento por caso serían doce acentos. La acción que
 * confirma va en tinta y la que vuelve, en contorno.
 *
 * A Client Component: resolver es la interacción por la que esta pantalla
 * existe. Cada clase ofrece exactamente las decisiones que la spec nombra, así
 * que a la persona nunca se le pide que escriba lo que el sistema ya sabe —
 * RF-30 para un producto desconocido, RF-31 para uno que dejó de venir, RF-29
 * para una fila que nadie pudo leer.
 *
 * Cómo salió se lee en dos lugares distintos, y el corte es el mismo que hace
 * `RevertCorrectionButton` por la misma razón (RF-22 de la 003). Una negativa
 * deja el panel donde estaba, así que su mensaje va adentro, sobre el caso que
 * no se resolvió. Decidir se lleva el caso puesto: `/revision` lista sólo lo
 * que sigue pendiente, así que la página refrescada lo saca de la cola y esta
 * confirmación se anuncia al toaster del layout, que es lo único que queda en
 * pantalla cuando el caso ya no está.
 */
export function CaseDetail({ item, mayCorrect, categories, suppliers }: CaseDetailProps) {
  const router = useRouter()
  const { addToast } = useToast()
  const [step, setStep] = useState(1)
  const [choiceId, setChoiceId] = useState<string | null>(null)
  const [price, setPrice] = useState(payloadText(item, 'price'))
  const [categoryId, setCategoryId] = useState('')
  // Lo que se escribe para cargar la fila a mano. Un solo objeto y no seis
  // estados: son los campos de un formulario, se limpian juntos y viajan juntos.
  const [form, setForm] = useState({
    number: payloadText(item, 'number'),
    date: '',
    total: '',
    supplierId: '',
    productText: '',
    quantity: '',
    amount: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Kept beside the message and not folded into it: a refusal about a
  // correction turns into a link and a name, and rewriting the sentence here to
  // slip either one inside it would be this component editing text the backend
  // wrote.
  const [refused, setRefused] = useState<RefusedByCorrection | null>(null)

  const fields = fieldsOf(item)
  const pending = item.status === 'PENDING'
  const choices = choicesOf(item)
  const chosen = choices.find(choice => choice.id === choiceId) ?? null
  // La carga a mano aparece **dentro** del paso 2 y sólo cuando se eligió esa
  // salida: la otra es darla por revisada, y ahí no hay nada que escribir.
  const loadable = LOADABLE_KINDS[item.kind as keyof typeof LOADABLE_KINDS] ?? null
  const control =
    item.kind === 'unreadable_row'
      ? 'price'
      : item.kind === 'unknown_category'
        ? 'category'
        : loadable !== null && choiceId === 'load'
          ? loadable
          : null
  const category = categories.find(one => String(one.id) === categoryId) ?? null
  const supplier = suppliers.find(one => String(one.id) === form.supplierId) ?? null
  /*
    Una decisión de éstas **no se guarda como regla**, y la diferencia importa.
    Una regla contesta sola la próxima vez que llegue lo mismo, y acá no hay
    próxima vez que sea lo mismo: la factura siguiente que el portal publique
    rota es otra factura, y elegir entre dos valores es una discusión sobre un
    registro y no sobre una clase de caso.
  */
  const remembered = !DISPUTED_KINDS.includes(item.kind) && choiceId !== 'load'

  /** Lo que se manda al backend, o `null` mientras la decisión esté incompleta. */
  const decision: Record<string, unknown> | null =
    control === 'price'
      ? price === ''
        ? null
        : { product_code: payloadText(item, 'product_code'), price }
      : control === 'category'
        ? category === null
          ? null
          : { category_id: category.id }
        : control === 'invoice'
          ? invoiceDecision(form, supplier)
          : control === 'order'
            ? orderDecision(form, supplier)
            : (chosen?.decision ?? null)

  const confirmLabel =
    control === 'price'
      ? 'Registrar este precio'
      : control === 'category'
        ? 'Asignar este rubro'
        : control === 'invoice'
          ? 'Cargar la factura'
          : control === 'order'
            ? 'Cargar la orden'
            : (chosen?.title ?? 'Confirmar')

  const impact = impactOf(item, { chosen, price, category, form, supplier })

  async function decide() {
    if (decision === null) return
    setSaving(true)
    setError(null)
    setRefused(null)
    const result = await resolveCase(item.id, decision, remembered)
    setSaving(false)
    if (result.ok) {
      addToast({
        type: 'success',
        title: 'Caso resuelto',
        description: 'La decisión quedó registrada y el caso sale de la cola.',
      })
      router.refresh()
      return
    }
    setError(result.message)
    setRefused(refusedByCorrection(result.details))
  }

  return (
    <div className="flex h-full flex-col gap-5 rounded-xl border border-border bg-card p-6">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="section-label">{caseKindLabel(item.kind)}</span>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>{sectionLabel(item.section)}</span>
            <span className="amount">{formatMoment(item.created_at)}</span>
            {item.occurrences > 1 && <span>se repitió {item.occurrences} veces</span>}
            {/*
              Cuánto hace que espera, y si eso ya es demasiado (RF-16, RF-17).
              El número lo calcula el backend contra el parámetro que el dueño
              mueve (RF-18), así que la pantalla no decide nada acá: lo muestra.
              Demorado es un estado del caso, así que es una píldora (`UI-03`).
            */}
            {pending && (
              <span>
                {item.waiting_days === 0
                  ? 'llegó hoy'
                  : `espera hace ${item.waiting_days} ${item.waiting_days === 1 ? 'día' : 'días'}`}
              </span>
            )}
            {pending && item.is_stale && <Badge tone="warn">Demorado</Badge>}
          </div>
        </div>
        <h2 className="text-lg font-semibold text-foreground">{item.reason}</h2>
      </header>

      {pending && <Stepper step={step} />}

      {step === 1 && (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-foreground">Qué trajo el portal</h3>
          {fields.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Este caso no trae más dato que su motivo.
            </p>
          ) : (
            <dl className="grid gap-4 rounded-lg border border-border bg-muted p-4 sm:grid-cols-2">
              {fields.map(field => (
                <div key={field.label} className={`min-w-0 ${field.wide ? 'sm:col-span-2' : ''}`}>
                  <dt className="section-label">{field.label}</dt>
                  <dd className="mt-1.5 text-sm text-foreground">{field.value}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>
      )}

      {step === 2 && (
        <section className="space-y-3">
          <h3 className="text-lg font-semibold text-foreground">{questionOf(item)}</h3>

          {choices.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2">
              {choices.map(choice => (
                <button
                  key={choice.id}
                  type="button"
                  aria-pressed={choice.id === choiceId}
                  onClick={() => setChoiceId(choice.id)}
                  className={`cursor-pointer rounded-lg border p-4 text-left ${
                    choice.id === choiceId
                      ? 'border-brand bg-background'
                      : 'border-border hover:bg-muted'
                  }`}
                >
                  <span className={`section-label ${choice.id === choiceId ? 'text-brand' : ''}`}>
                    {choice.overline}
                  </span>
                  <span className="mt-2 block text-sm font-semibold text-foreground">
                    {choice.title}
                  </span>
                  <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">
                    {choice.detail}
                  </span>
                </button>
              ))}
            </div>
          )}

          {control === 'price' && (
            <div className="space-y-1.5">
              {/*
                El rótulo visible **es** el nombre accesible: sin `aria-label`
                encima, que es lo que hace que quien maneja la pantalla por voz
                pueda nombrar el campo que está viendo.
              */}
              <label className="block text-sm font-medium text-foreground" htmlFor="precio">
                Precio
              </label>
              <p className="text-xs text-muted-foreground">El que la fila no dejó leer.</p>
              <Input
                id="precio"
                className="max-w-48"
                type="number"
                min={0}
                value={price}
                onChange={event => setPrice(event.target.value)}
              />
            </div>
          )}

          {control === 'category' && (
            /*
              RF-14 de la 010: la forma escrita que nadie decidió se resuelve
              **acá**, en la misma pantalla donde compras ya resuelve todo lo que
              la actualización aparta.
            */
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-foreground" htmlFor="rubro">
                Rubro
              </label>
              <p className="text-xs text-muted-foreground">
                Elegí a cuál pertenece la forma escrita que llegó.
              </p>
              <select
                id="rubro"
                className={`${selectClassName} max-w-64`}
                value={categoryId}
                onChange={event => setCategoryId(event.target.value)}
              >
                <option value="">Elegí un rubro…</option>
                {categories.map(one => (
                  <option key={one.id} value={String(one.id)}>
                    {one.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {(control === 'invoice' || control === 'order') && (
            <div className="grid gap-3 rounded-lg border border-border bg-muted p-4 sm:grid-cols-2">
              {suppliers.length === 0 ? (
                <p className="text-sm text-muted-foreground sm:col-span-2">
                  Para cargarla hace falta el padrón de proveedores, y esta sesión no lo alcanza.
                  Puede hacerlo compras o el dueño.
                </p>
              ) : (
                <>
                  <Field id="carga-numero" label="Número">
                    <Input
                      id="carga-numero"
                      value={form.number}
                      onChange={event => setForm({ ...form, number: event.target.value })}
                    />
                  </Field>
                  <Field
                    id="carga-fecha"
                    label={control === 'invoice' ? 'Fecha de emisión' : 'Fecha de la orden'}
                  >
                    <Input
                      id="carga-fecha"
                      type="date"
                      value={form.date}
                      onChange={event => setForm({ ...form, date: event.target.value })}
                    />
                  </Field>
                  <Field id="carga-proveedor" label="Proveedor">
                    <select
                      id="carga-proveedor"
                      className={selectClassName}
                      value={form.supplierId}
                      onChange={event => setForm({ ...form, supplierId: event.target.value })}
                    >
                      <option value="">Elegí un proveedor…</option>
                      {suppliers.map(one => (
                        <option key={one.id} value={String(one.id)}>
                          {one.legal_name}
                        </option>
                      ))}
                    </select>
                  </Field>
                  {control === 'invoice' ? (
                    <Field id="carga-total" label="Total">
                      <Input
                        id="carga-total"
                        type="number"
                        min={0}
                        step="0.01"
                        value={form.total}
                        onChange={event => setForm({ ...form, total: event.target.value })}
                      />
                    </Field>
                  ) : (
                    <>
                      <Field id="carga-importe" label="Importe (si lo sabés)">
                        <Input
                          id="carga-importe"
                          type="number"
                          min={0}
                          step="0.01"
                          value={form.amount}
                          onChange={event => setForm({ ...form, amount: event.target.value })}
                        />
                      </Field>
                      <Field id="carga-producto" label="Producto (si lo sabés)">
                        <Input
                          id="carga-producto"
                          value={form.productText}
                          onChange={event => setForm({ ...form, productText: event.target.value })}
                        />
                      </Field>
                      <Field id="carga-cantidad" label="Cantidad (si la sabés)">
                        <Input
                          id="carga-cantidad"
                          type="number"
                          min={0}
                          value={form.quantity}
                          onChange={event => setForm({ ...form, quantity: event.target.value })}
                        />
                      </Field>
                    </>
                  )}
                  {/*
                    El vencimiento no se pide y no es un olvido: sale del plazo
                    acordado con el proveedor, igual que el de cualquier otra
                    factura (RF-26 de 005). Preguntarlo acá sería dejar que una
                    factura cargada a mano tenga una regla distinta que el resto.
                  */}
                  {control === 'invoice' && (
                    <p className="text-xs text-muted-foreground sm:col-span-2">
                      El vencimiento no se escribe: sale del plazo acordado con el proveedor, como
                      en todas las demás.
                    </p>
                  )}
                </>
              )}
            </div>
          )}

          {choices.length === 0 && control === null && (
            <p className="text-sm text-muted-foreground">
              Esta clase de caso todavía no tiene una decisión en pantalla.
            </p>
          )}
        </section>
      )}

      {step === 3 && (
        <section className="space-y-3">
          <div className="rounded-lg border border-border bg-muted p-4">
            <h3 className="text-sm font-semibold text-foreground">Qué pasa si confirmás</h3>
            <div className="mt-3 flex flex-wrap gap-x-8 gap-y-3">
              {impact.figures.map(figure => (
                <div key={figure.label}>
                  <div
                    className={`amount text-lg ${figure.tone === 'ok' ? 'text-ok' : 'text-foreground'}`}
                  >
                    {figure.value}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">{figure.label}</div>
                </div>
              ))}
            </div>
            <p className="mt-3 text-sm text-foreground">{impact.sentence}</p>
          </div>
          {/*
            Lo que hace que la cola se vacíe en vez de repetirse, dicho antes de
            confirmar y no después: la decisión se guarda como regla, se aplica
            sola a los casos iguales, y dejarla sin efecto devuelve éste a la
            cola (RF-34, RF-37).
          */}
          {remembered ? (
            <p className="text-xs text-muted-foreground">
              Queda como decisión guardada: se aplica sola a los casos iguales, y dejarla sin efecto
              devuelve este caso a la cola.
            </p>
          ) : (
            <p className="text-xs text-muted-foreground">
              Esta decisión vale sólo para este caso: no se guarda como regla, porque el próximo no
              va a ser el mismo.
            </p>
          )}
        </section>
      )}

      {/*
        La salida que el diseño pone antes de los botones, y que es cierta: un
        caso sin resolver sigue contado acá y ningún total lo usa. Es el
        Artículo II dicho en la pantalla donde la persona duda (`UI-07`).
      */}
      {pending && step > 1 && (
        <Notice tone="warn" title="Si no estás seguro, dejalo pendiente.">
          Sigue contado acá y ningún total lo usa hasta que se resuelva.
        </Notice>
      )}

      {/*
        The refusal, then who is behind it, then where to go about it. The panel
        stays exactly where it was — the case was not resolved, so `/revision`
        still lists it — and the amount the person typed is still in the field,
        which is the difference between being told and being sent back to the
        start.

        Whoever may not change a correction is told who may, instead of being
        left in front of an instruction with nobody attached to it: the message
        says the correction has to be changed, and purchasing — who empties this
        queue — cannot change one. Hiding the link and saying nothing else would
        be half the decision.
      */}
      {error && (
        <Notice tone="danger" title={error}>
          {refused !== null && (
            <>
              {refused.correctedBy !== null && <p>La corrección la hizo {refused.correctedBy}.</p>}
              {/*
               * `RF-13`: los dos son enlaces porque llevan a otra pantalla. Lo
               * que **cambia** una corrección es el botón que está allá.
               */}
              <p className="mt-1 flex flex-wrap gap-4">
                <Link className="text-link hover:underline" href={`/precios/${refused.productId}`}>
                  Ver la corrección
                </Link>
                {mayCorrect && (
                  <Link
                    className="text-link hover:underline"
                    href={`/precios/${refused.productId}#correcciones`}
                  >
                    Cambiarla
                  </Link>
                )}
              </p>
              {!mayCorrect && (
                <p className="mt-1">
                  Cambiar una corrección es de quien maneja el catálogo: el dueño o ventas.
                </p>
              )}
            </>
          )}
        </Notice>
      )}

      {pending && (
        <div className="mt-auto flex flex-wrap items-center justify-end gap-2.5 pt-2">
          {step > 1 && (
            <Button variant="outline" disabled={saving} onClick={() => setStep(step - 1)}>
              Atrás
            </Button>
          )}
          {/*
            Sin `title` explicativo a propósito: un botón deshabilitado no
            recibe el puntero, así que el globo no aparecería nunca. Lo que
            falta lo dice el paso, arriba.
          */}
          {step < 3 && (
            <Button disabled={step === 2 && decision === null} onClick={() => setStep(step + 1)}>
              Siguiente
            </Button>
          )}
          {step === 3 && (
            <Button disabled={saving || decision === null} onClick={decide}>
              {confirmLabel}
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

/** Un campo del formulario de carga: su rótulo visible es su nombre accesible. */
function Field({ id, label, children }: { id: string; label: string; children: ReactNode }) {
  return (
    <div className="min-w-0 space-y-1.5">
      <label className="block text-sm font-medium text-foreground" htmlFor={id}>
        {label}
      </label>
      {children}
    </div>
  )
}

/** Los tres pasos, y en cuál se está (guía visual `3d`). */
function Stepper({ step }: { step: number }) {
  return (
    <div className="flex items-center gap-3">
      {STEPS.map((_, index) => {
        const number = index + 1
        return (
          <Fragment key={number}>
            {number > 1 && (
              <span
                aria-hidden
                className={`h-px flex-1 ${number <= step ? 'bg-primary' : 'bg-border'}`}
              />
            )}
            <span
              aria-hidden
              className={`flex size-6 flex-none items-center justify-center rounded-full font-mono text-[11px] font-semibold ${
                number <= step
                  ? 'bg-primary text-primary-foreground'
                  : 'border border-input text-muted-foreground'
              }`}
            >
              {number}
            </span>
          </Fragment>
        )
      })}
      <span className="ml-1.5 text-[11.5px] text-muted-foreground">
        Paso {step} de {STEPS.length} · {STEPS[step - 1]}
      </span>
    </div>
  )
}

/**
 * Qué se mueve si se confirma, con las cifras que el caso trae.
 *
 * Nada estimado: los productos que esperan una forma escrita salen del
 * `payload`, el precio es el que la persona acaba de escribir, y las veces que
 * llegó la misma fila las cuenta el backend. Lo que el caso no trae se dice en
 * palabras y no con un número inventado.
 */
function impactOf(
  item: Case,
  {
    chosen,
    price,
    category,
    form,
    supplier,
  }: {
    chosen: Choice | null
    price: string
    category: Category | null
    form: LoadForm
    supplier: Supplier | null
  }
): { figures: Figure[]; sentence: string } {
  const undo: Figure = { value: 'Sí', label: 'se puede deshacer', tone: 'ok' }
  const products = item.payload.products

  /*
    La carga a mano **no se deshace**, y por eso no dice que sí. Deshacer una
    decisión guardada devuelve el caso a la cola; no borra la factura que
    entró. Lo que sí se puede es corregirla después desde su ficha, y eso es
    otra cosa — decirlo como «se puede deshacer» sería prometer lo que no es.
  */
  if (chosen?.id === 'load') {
    const invoice = item.kind === 'unreadable_invoice_row'
    const figures: Figure[] = []
    if (invoice && form.total !== '') {
      figures.push({ value: formatPrice(form.total), label: 'entra al catálogo de facturas' })
    }
    return {
      figures,
      sentence:
        supplier === null
          ? 'Completá los datos para ver qué se registra.'
          : invoice
            ? `Queda registrada a nombre de ${supplier.legal_name}, marcada como cargada a mano, y su vencimiento sale del plazo acordado con ese proveedor. Si más adelante el portal la publica diciendo otra cosa, se va a preguntar cuál de los dos valores queda.`
            : `Queda registrada a nombre de ${supplier.legal_name}, marcada como cargada a mano. Como la plataforma no la vio llegar, se mide desde cuándo se emitió y no desde cuándo está en su estado.`,
    }
  }

  if (DISPUTED_KINDS.includes(item.kind)) {
    return {
      figures: [],
      sentence:
        chosen === null
          ? 'Elegí cuál de los dos valores queda.'
          : chosen.id === 'portal'
            ? 'Los valores del portal pisan a los que se habían cargado a mano, y el registro pasa a contar como leído del portal.'
            : 'Quedan los valores cargados a mano. La pregunta no vuelve a menos que el portal publique algo distinto de lo que acabás de rechazar.',
    }
  }

  if (item.kind === 'unknown_category') {
    const figures: Figure[] = []
    if (typeof products === 'number') {
      figures.push({
        value: String(products),
        label: products === 1 ? 'producto queda clasificado' : 'productos quedan clasificados',
      })
    }
    figures.push(undo)
    return {
      figures,
      sentence:
        category === null
          ? 'Elegí un rubro para ver qué se mueve.'
          : `«${payloadText(item, 'category_text')}» pasa a ser ${category.name}, y esa forma escrita no se vuelve a preguntar.`,
    }
  }

  if (item.kind === 'unreadable_row') {
    return {
      figures: [
        { value: price === '' ? '—' : formatPrice(price), label: 'queda registrado' },
        undo,
      ],
      sentence:
        price === ''
          ? 'Escribí el precio para ver qué se mueve.'
          : `El código ${payloadText(item, 'product_code')} queda con ese precio, que es el que van a usar los totales.`,
    }
  }

  const figures: Figure[] = []
  if (item.occurrences > 1) {
    figures.push({ value: String(item.occurrences), label: 'veces que llegó lo mismo' })
  }
  figures.push(undo)
  return {
    figures,
    sentence: chosen?.detail ?? 'Elegí una decisión para ver qué se mueve.',
  }
}
