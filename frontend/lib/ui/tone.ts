/**
 * De qué tono es cada estado del negocio (`RF-06`, `RF-07`, `UI-03`).
 *
 * Es **el** mapa, no *un* mapa. Mientras cada pantalla elija su color, «vencida»
 * se dibuja de tres maneras distintas y nadie se entera: la lista la pinta roja,
 * el calendario ámbar y la ficha del proveedor gris. Con el mapa acá, cambiar
 * qué significa un estado es editar una línea de este archivo.
 *
 * **Cinco tonos, y ninguno es el naranja de marca.** El naranja dice «decidí
 * acá» y es de los botones: si además dijera «vencida», la pantalla dejaría de
 * poder distinguir un dato urgente de una acción principal, que es lo único que
 * el color tiene que hacer acá.
 *
 * | Tono | Qué significa |
 * |---|---|
 * | `ok` | Está resuelto, no hay nada que hacer |
 * | `info` | Está pasando algo, y es sólo información |
 * | `warn` | Requiere una decisión de una persona |
 * | `danger` | Algo no cierra o venció |
 * | `neutral` | Sin novedad: archivado, descartado, todavía sin empezar |
 *
 * A eso se suma el **punteado** (`draft`), que no es un sexto color sino otra
 * pregunta: si el dato lo confirmó una persona o todavía no (`RF-08`). Por eso
 * `pill()` lo aplica encima del tono en vez de reemplazar la tabla.
 *
 * Importa **sólo** los tipos generados del backend (`lib/api/types.ts`): un
 * mapa que dependiera de `lib/purchases/` o de `lib/sales/` volvería a atar el
 * vocabulario compartido a un dominio, que es de lo que se lo está sacando.
 */
import type { components } from '@/lib/api/types'

type Schemas = components['schemas']

/** Los cinco significados del color. El naranja de marca no es uno. */
export type Tone = 'neutral' | 'ok' | 'info' | 'warn' | 'danger'

/** Lo que `Badge` acepta: los cinco tonos, más el punteado de `RF-08`. */
export type BadgeTone = Tone | 'draft'

/**
 * El tono de una píldora, punteado cuando el dato todavía no lo confirmó nadie.
 *
 * Se llama con la señal ya resuelta —`pill(saleTone(s), isUnconfirmedSale(s))`—
 * para que la pantalla no tenga que acordarse de las dos cosas por separado.
 */
export function pill(tone: Tone, unconfirmed = false): BadgeTone {
  return unconfirmed ? 'draft' : tone
}

/*
 * --- Compras ---------------------------------------------------------------
 */

/**
 * El estado de pago de una factura.
 *
 * `PARCIAL` es `warn` y no `info` porque una factura pagada a medias es trabajo
 * pendiente, no una noticia. Sale del calendario, que ya lo dibujaba así, y es
 * el que las tres pantallas de `RF-06` tienen que compartir.
 *
 * Llega como `string` y no como enum: el backend lo publica sin tipar.
 */
const PAYMENT_TONES: Record<string, Tone> = {
  SALDADA: 'ok',
  PARCIAL: 'warn',
  SIN_PAGOS: 'neutral',
  INCONSISTENTE: 'danger',
}

export function invoicePaymentTone(state: string | null | undefined): Tone {
  return (state && PAYMENT_TONES[state]) || 'neutral'
}

/**
 * Si una factura se puede dar por buena tal como está.
 *
 * `PENDING` es `warn` —espera a una persona— y `RESOLVED` es `info`: alguien ya
 * decidió, y eso es historia del dato, no un estado que pida algo.
 */
const INVOICE_REVIEW_TONES: Record<Schemas['InvoiceReviewState'], Tone> = {
  OK: 'ok',
  PENDING: 'warn',
  RESOLVED: 'info',
}

export function invoiceReviewTone(state: Schemas['InvoiceReviewState']): Tone {
  return INVOICE_REVIEW_TONES[state]
}

/** Lo mismo para una orden de compra: el enum es otro, la lectura es la misma. */
const ORDER_REVIEW_TONES: Record<Schemas['OrderReviewState'], Tone> = {
  OK: 'ok',
  PENDING: 'warn',
  RESOLVED: 'info',
}

export function orderReviewTone(state: Schemas['OrderReviewState']): Tone {
  return ORDER_REVIEW_TONES[state]
}

/**
 * Un pago imputado, esperando o anulado.
 *
 * `VOIDED` es `neutral` y no `danger`: anular un pago es una decisión tomada a
 * propósito, no algo que salió mal.
 */
const PAYMENT_STATE_TONES: Record<Schemas['PaymentState'], Tone> = {
  IMPUTED: 'ok',
  PENDING: 'warn',
  VOIDED: 'neutral',
}

export function paymentTone(state: Schemas['PaymentState']): Tone {
  return PAYMENT_STATE_TONES[state]
}

/**
 * En qué anda un vencimiento del calendario.
 *
 * Los tres son excluyentes y están en orden de quién tapa a quién: el que venció
 * sin recibo es el que pide algo, y «ya pasó» no se dice cuando la roja ya lo
 * está diciendo más fuerte. Devuelve `null` cuando no hay nada que señalar.
 */
export function dueDateTone(entry: {
  is_overdue_without_receipt: boolean
  receipt_issued: boolean
  is_past: boolean
}): { label: string; tone: Tone } | null {
  if (entry.is_overdue_without_receipt) return { label: 'Venció sin recibo', tone: 'danger' }
  if (entry.receipt_issued) return { label: 'Recibo emitido', tone: 'ok' }
  if (entry.is_past) return { label: 'Ya pasó', tone: 'warn' }
  return null
}

/*
 * --- Ventas ----------------------------------------------------------------
 */

/**
 * Si una venta se puede sumar.
 *
 * `HELD` es lo apartado —lo que el sistema no pudo interpretar y guardó en vez
 * de descartar (Artículo II)—, y `DISCARDED` es lo que una persona ya decidió
 * dejar afuera: por eso el primero pide algo y el segundo no.
 */
const SALE_TONES: Record<Schemas['SaleState'], Tone> = {
  COUNTED: 'ok',
  HELD: 'warn',
  DISCARDED: 'neutral',
}

export function saleTone(state: Schemas['SaleState']): Tone {
  return SALE_TONES[state]
}

/*
 * --- Catálogo --------------------------------------------------------------
 */

/** Un producto vigente o dado de baja. */
const PRODUCT_TONES: Record<Schemas['ProductStatus'], Tone> = {
  ACTIVE: 'ok',
  DISCONTINUED: 'neutral',
}

export function productTone(status: Schemas['ProductStatus']): Tone {
  return PRODUCT_TONES[status]
}

/**
 * Una corrección de precio: en vigencia, en conflicto o devuelta.
 *
 * `CONFLICTED` es `warn` porque es exactamente el caso que espera a una persona:
 * el portal publicó otro valor debajo de una corrección que sigue puesta.
 */
const CORRECTION_TONES: Record<Schemas['CorrectionStatus'], Tone> = {
  ACTIVE: 'ok',
  CONFLICTED: 'warn',
  REVERTED: 'neutral',
}

export function correctionTone(status: Schemas['CorrectionStatus']): Tone {
  return CORRECTION_TONES[status]
}

/*
 * --- Revisión, buzón y sistema ---------------------------------------------
 */

/** Un caso de la cola de revisión. */
const CASE_TONES: Record<Schemas['CaseStatus'], Tone> = {
  PENDING: 'warn',
  RESOLVED: 'ok',
}

export function caseTone(status: Schemas['CaseStatus']): Tone {
  return CASE_TONES[status]
}

/** Un mensaje del buzón. Se lee igual que un caso: o espera a alguien, o no. */
const MESSAGE_TONES: Record<Schemas['MessageState'], Tone> = {
  PENDING: 'warn',
  RESOLVED: 'ok',
}

export function messageTone(state: Schemas['MessageState']): Tone {
  return MESSAGE_TONES[state]
}

/**
 * Una corrida de un trabajo automático.
 *
 * `RUNNING` es `info` —está pasando ahora y no hay nada que decidir— y `PENDING`
 * es `neutral`: todavía no empezó.
 */
const JOB_TONES: Record<Schemas['JobStatus'], Tone> = {
  PENDING: 'neutral',
  RUNNING: 'info',
  SUCCEEDED: 'ok',
  FAILED: 'danger',
}

export function jobTone(status: Schemas['JobStatus']): Tone {
  return JOB_TONES[status]
}

/** Cómo está un servicio del que dependemos. `off` es apagado a propósito. */
const HEALTH_TONES: Record<Schemas['HealthState'], Tone> = {
  ok: 'ok',
  down: 'danger',
  off: 'neutral',
}

export function healthTone(state: Schemas['HealthState']): Tone {
  return HEALTH_TONES[state]
}

/*
 * --- Lo que todavía no confirmó nadie (`RF-08`) -----------------------------
 *
 * Cada predicado dice, para una entidad, si lo que se muestra lo puso una
 * persona o lo dedujo el sistema y todavía nadie lo miró. Están acá y no en la
 * pantalla por la misma razón que los tonos: la respuesta tiene que ser la
 * misma en las cuatro pantallas donde la entidad aparece.
 *
 * Una entidad que no tiene ninguna de estas señales **no se puntea**: no hay
 * forma de inventar la diferencia entre confirmado y sin confirmar cuando el
 * backend no la publica.
 */

/** Una venta estimada, o apartada sin que nadie la haya mirado todavía. */
export function isUnconfirmedSale(sale: {
  state: Schemas['SaleState']
  is_estimated: boolean
}): boolean {
  return sale.is_estimated || sale.state === 'HELD'
}

/** Un vencimiento cargado a mano: no salió de ninguna factura del portal. */
export function isUnconfirmedDueDate(origin: Schemas['DueDateOrigin']): boolean {
  return origin === 'MANUAL'
}

/** Un pago cargado a mano, que el portal todavía no informó. */
export function isUnconfirmedPayment(origin: Schemas['PaymentOrigin']): boolean {
  return origin === 'MANUAL'
}

/** Un precio puesto por la plataforma y no publicado por el portal. */
export function isUnconfirmedPrice(source: Schemas['PriceSource']): boolean {
  return source === 'SYSTEM'
}

/**
 * Una grafía de proveedor que nadie confirmó.
 *
 * `OBSERVED` es la que el sistema vio pasar y nadie miró; `LEARNED` salió de una
 * decisión que **tomó una persona** —es lo que dice la ficha del proveedor sobre
 * cada una: «reconocida por el sistema» contra «asignada por una persona»—, así
 * que está confirmada y no va punteada.
 *
 * `tasks.md` (tarea 3) las nombra a las dos como sin confirmar. Se implementa
 * sólo `OBSERVED` y queda anotado para el `Lead`: el enum de proveedores no
 * tiene `SEED`, así que puntear las dos dejaría **todas** las grafías punteadas,
 * y una señal que aparece siempre no distingue nada, que es justo lo que `RF-08`
 * pide.
 */
export function isUnconfirmedSupplierAlias(source: Schemas['SupplierAliasSource']): boolean {
  return source === 'OBSERVED'
}

/** Una equivalencia de rubro aprendida de una decisión, no sembrada. */
export function isUnconfirmedCategoryAlias(source: Schemas['AliasSource']): boolean {
  return source === 'LEARNED'
}
