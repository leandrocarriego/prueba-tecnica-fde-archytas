/**
 * Every date on screen, in the only timezone this business has.
 *
 * The API sends instants with their offset (`2026-08-29T21:51:31+00:00`), which
 * is unambiguous — and then `toLocaleString('es-AR')` renders it in *the
 * runtime's* timezone, because a locale sets the format and not the zone. The
 * server container has no `TZ`, so it was UTC: the prices screen said 21:51 for
 * an update that happened at 18:51.
 *
 * Two bugs in one. The visible one is the three hours. The other is that a
 * Server Component rendered UTC and the browser would have hydrated the same
 * instant in the visitor's zone — the same markup rendering differently on the
 * two sides, which is a hydration mismatch waiting for the first user outside
 * Argentina.
 *
 * So the zone is pinned here and nowhere else. It is not a preference: the
 * ferretería is in Buenos Aires, the supplier publishes on that clock, and
 * `celery_app` already schedules on it. A date read by somebody standing in the
 * shop has one correct value.
 */
export const BUSINESS_TIME_ZONE = 'America/Argentina/Buenos_Aires'

/**
 * 24-hour on purpose. `es-AR` renders 12-hour with a marker that is easy to
 * lose at the end of a line, and `09:51` for `21:51` is worse than a format
 * nobody comments on.
 */
const BASE = {
  timeZone: BUSINESS_TIME_ZONE,
  hour12: false,
} as const

/**
 * The day, spelled out. Not `dateStyle: 'short'`, which drops the year to two
 * digits: this is a price list, and the year of a price is worth its four
 * characters.
 */
const DAY_PARTS = {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
} as const

/** A full moment: the day and the time it happened. */
export const MOMENT_FORMAT = new Intl.DateTimeFormat('es-AR', {
  ...BASE,
  ...DAY_PARTS,
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
})

/** The same, without the seconds, for tables with one row per event. */
export const SHORT_MOMENT_FORMAT = new Intl.DateTimeFormat('es-AR', {
  ...BASE,
  ...DAY_PARTS,
  hour: '2-digit',
  minute: '2-digit',
})

/** A date with no time, for the history of a product. */
export const DAY_FORMAT = new Intl.DateTimeFormat('es-AR', { ...BASE, ...DAY_PARTS })

/** A time with no date, for something that just happened. */
export const CLOCK_FORMAT = new Intl.DateTimeFormat('es-AR', {
  ...BASE,
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
})

/**
 * A plain date — `2026-06-17` — written the way the team reads it.
 *
 * Split rather than parsed on purpose, and this is the one place where that is
 * the right answer. `new Date('2026-06-17')` is midnight **UTC**, which in
 * Buenos Aires is nine at night of the sixteenth: a due date shown one day
 * early, every time, for a value that never had a time of day to begin with.
 *
 * A due date, an invoice date and a sale date are days, not instants. There is
 * no zone to convert them into, so none is applied.
 */
export function formatPlainDate(value: string | null | undefined): string {
  if (!value) return '—'
  const [year, month, day] = value.slice(0, 10).split('-')
  return year && month && day ? `${day}/${month}/${year}` : '—'
}

/** Los doce meses, como se rotula un eje: cortos y en versalita. */
const MONTH_LABELS = [
  'ENE',
  'FEB',
  'MAR',
  'ABR',
  'MAY',
  'JUN',
  'JUL',
  'AGO',
  'SEP',
  'OCT',
  'NOV',
  'DIC',
]

/**
 * El mes de un eje: `2026-08-01` → `AGO`, o `AGO 26` cuando hace falta el año.
 *
 * Se parte el string en vez de parsearlo, por la misma razón que
 * `formatPlainDate`: un mes del negocio no tiene hora, así que no hay ninguna
 * zona a la que convertirlo, y `new Date('2026-01-01')` en Buenos Aires es el
 * 31 de diciembre — un eje corrido un mes entero, todos los eneros.
 *
 * El año va sólo donde el eje lo necesita —el primer mes, y cada enero—, que es
 * lo que hace legible una serie que arranca en 2023 sin repetir el año catorce
 * veces.
 */
export function formatMonth(value: string | null | undefined, withYear = false): string {
  if (!value) return '—'
  const [year, month] = value.slice(0, 10).split('-')
  const label = MONTH_LABELS[Number(month) - 1]
  if (!label) return '—'
  return withYear && year ? `${label} ${year.slice(2)}` : label
}
