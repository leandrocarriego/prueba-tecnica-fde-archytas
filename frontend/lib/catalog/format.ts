/**
 * How prices, dates and variations are written on screen.
 *
 * In one place because the same number appears in the list, in the product page
 * and in the review screen, and three roundings of the same peso amount is how
 * a user stops trusting a system.
 */

const PESOS = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  maximumFractionDigits: 0,
})

const PERCENT = new Intl.NumberFormat('es-AR', {
  maximumFractionDigits: 1,
  signDisplay: 'exceptZero',
})

/** A price as the supplier publishes it: pesos, no cents. */
export function formatPrice(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const amount = typeof value === 'string' ? Number(value) : value
  return Number.isNaN(amount) ? '—' : PESOS.format(amount)
}

/** A percentage change, with its sign. */
export function formatVariation(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const amount = typeof value === 'string' ? Number(value) : value
  return Number.isNaN(amount) ? '—' : `${PERCENT.format(amount)}%`
}

/** A moment, in the format the team reads. */
export function formatMoment(value: string | null | undefined): string {
  if (!value) return '—'
  const moment = new Date(value)
  return Number.isNaN(moment.getTime()) ? '—' : moment.toLocaleString('es-AR')
}

/** A date without its time, for the history of a product. */
export function formatDay(value: string | null | undefined): string {
  if (!value) return '—'
  const moment = new Date(value)
  return Number.isNaN(moment.getTime()) ? '—' : moment.toLocaleDateString('es-AR')
}

/** Whether a variation is a rise, a fall or neither. */
export function variationTone(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return 'text-muted-foreground'
  const amount = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(amount) || amount === 0) return 'text-muted-foreground'
  return amount > 0 ? 'text-red-600' : 'text-emerald-600'
}
