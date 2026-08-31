/**
 * How the states of purchases are written on screen.
 *
 * In one place because the same state appears on the invoices list, on the
 * invoice page and on the calendar, and three names for the same thing is how
 * a person stops trusting a screen.
 */
import type { Invoice } from '@/lib/purchases/types'

const PAYMENT_STATES: Record<string, string> = {
  SALDADA: 'Saldada',
  PARCIAL: 'Pago parcial',
  SIN_PAGOS: 'Sin pagos',
  INCONSISTENTE: 'Inconsistente',
}

const REVIEW_STATES: Record<string, string> = {
  OK: 'En orden',
  PENDING: 'En revisión',
  RESOLVED: 'Resuelta',
}

/** What the payment state of an invoice is called. */
export function paymentStateLabel(state: string): string {
  return PAYMENT_STATES[state] ?? state
}

/** What the review state of an invoice is called. */
export function reviewStateLabel(state: string): string {
  return REVIEW_STATES[state] ?? state
}

/**
 * En qué formato llegó la factura, en una palabra (RF-05 de 004).
 *
 * El criterio firmado pide que la lista distinga **a simple vista** cuáles
 * llegaron como imagen escaneada, y son 46 de cada 100: son las que el lector
 * acierta menos y las que más caen en revisión, así que quien mira la lista
 * necesita saber cuál es cuál sin abrir ninguna.
 *
 * Lo que llega es lo que escribió el portal en su columna *Tipo* —`PDF`,
 * `PDF (escaneado)`, `Excel`—, y se traduce acá en vez de guardarse traducido:
 * el día que el portal escriba otra cosa, esto la muestra tal cual en lugar de
 * perderla.
 */
export function fileKindLabel(kind: string | null | undefined): string {
  if (!kind) return '—'
  const normalized = kind.toLowerCase()
  if (normalized.includes('escane') || normalized.includes('scan')) return 'Escaneada'
  if (normalized.includes('excel') || normalized.includes('planilla')) return 'Planilla'
  if (normalized.includes('pdf')) return 'PDF'
  return kind
}

/** Si el formato es el difícil, el que conviene que salte a la vista. */
export function isScanned(kind: string | null | undefined): boolean {
  const normalized = (kind ?? '').toLowerCase()
  return normalized.includes('escane') || normalized.includes('scan')
}

/**
 * Todo lo que anda mal con una factura, y no sólo lo primero.
 *
 * Antes esto devolvía **un** señalamiento por precedencia, y ahí se perdía uno
 * real: una factura inconsistente que además contradice al portal mostraba la
 * inconsistencia y callaba la contradicción, aunque RF-46 pida ver las dos
 * cosas. Los cuatro son independientes entre sí —una decisión pendiente, un
 * número que no cierra, un plazo que pasó y un origen que dice otra cosa— y no
 * hay motivo para que uno tape a otro.
 *
 * Sigue el orden de lo que hay que hacer primero, porque el orden en que se
 * leen sí importa.
 */
export function warningsFor(invoice: Invoice): string[] {
  const warnings: string[] = []
  if (invoice.review_state === 'PENDING') {
    warnings.push(invoice.review_reason ?? 'Esperando una decisión')
  }
  if (invoice.is_inconsistent) warnings.push('Los pagos superan el total de la factura')
  if (invoice.is_overdue_without_receipt) warnings.push('Venció sin recibo de recepción')
  if (invoice.payment_state_disagrees) {
    warnings.push(`El portal la informa como «${invoice.portal_payment_status}»`)
  }
  return warnings
}
