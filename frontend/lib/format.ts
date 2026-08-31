/**
 * How money, percentages and days are written across the whole platform.
 *
 * `lib/catalog/format.ts` was this file when prices were the only screen. It
 * still exports what it always did — nothing that imports it had to change —
 * and the shared half lives here, because invoices, payments, orders and the
 * dashboard write the same peso amount and it must not be rounded three ways.
 *
 * Dates are **not** formatted here: `lib/time.ts` is the one file allowed to
 * know a timezone, and there is a test that says so.
 */
import { formatPlainDate } from '@/lib/time'

const PESOS = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  maximumFractionDigits: 0,
})

const WHOLE = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 })

const DECIMAL = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1 })

/** An amount in pesos, without cents — which is how the portal publishes them. */
export function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const amount = typeof value === 'string' ? Number(value) : value
  return Number.isNaN(amount) ? '—' : PESOS.format(amount)
}

/** A plain count. */
export function count(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : WHOLE.format(value)
}

/** A number with at most one decimal — an average of days, a percentage. */
export function decimal(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const amount = typeof value === 'string' ? Number(value) : value
  return Number.isNaN(amount) ? '—' : DECIMAL.format(amount)
}

/** A day the business reads: a due date, an invoice date, the day of a sale. */
export const day = formatPlainDate

/**
 * How many days there are between a day and today, signed.
 *
 * Positive is in the future. Both ends are read as plain days, so nothing here
 * depends on the hour or on the zone the process happens to run in.
 */
export function daysFromToday(value: string | null | undefined): number | null {
  if (!value) return null
  const [year, month, dayOfMonth] = value.slice(0, 10).split('-').map(Number)
  if (!year || !month || !dayOfMonth) return null
  const target = Date.UTC(year, month - 1, dayOfMonth)
  const now = new Date()
  const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())
  return Math.round((target - today) / 86_400_000)
}
