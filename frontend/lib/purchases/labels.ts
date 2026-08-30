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
 * The one line that says everything that is wrong with an invoice, or nothing.
 *
 * Ordered by what a person has to do first: a held invoice is a decision, an
 * inconsistent one is a number that does not close, and one overdue without a
 * receipt is a deadline that already passed.
 */
export function warningFor(invoice: Invoice): string | null {
  if (invoice.review_state === 'PENDING') return invoice.review_reason ?? 'Esperando una decisión'
  if (invoice.is_inconsistent) return 'Los pagos superan el total de la factura'
  if (invoice.is_overdue_without_receipt) return 'Venció sin recibo de recepción'
  if (invoice.payment_state_disagrees) {
    return `El portal la informa como «${invoice.portal_payment_status}»`
  }
  return null
}
