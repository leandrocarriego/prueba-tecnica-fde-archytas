/**
 * El control de mes del calendario (RF-05).
 *
 * Vive acá y no dentro de la pantalla porque es la única lógica de la 006 que
 * el frontend calcula por su cuenta: la ventana que se va a pedir. Todo lo
 * demás que se ve en el calendario lo decide el backend. Separada, se puede
 * fijar con un test sin levantar una página entera.
 */

/** Los filtros de la pantalla, tal como viajan en la URL. */
export interface CalendarFilters {
  sin_recibo?: string
  saldadas?: string
}

/** Cuántos vencimientos de un día se muestran antes de recortar (RF-08). */
export const PER_DAY = 4

/**
 * El código con el que el backend dice que la fecha nueva ya pasó (RF-25).
 *
 * Es lo único que la pantalla tiene que **reconocer** de una negativa en vez de
 * sólo mostrarla: RF-25 la convierte en una pregunta. Viaja como código dentro
 * de `details` y no como el texto del mensaje, porque comparar el castellano
 * haría de la redacción un contrato que nadie declaró — y reescribir el mensaje
 * mataría la confirmación en silencio, dejando un movimiento legítimo como
 * error. El otro lado es `MOVING_INTO_THE_PAST_CODE`, en `purchases/service.py`.
 */
export const MOVING_INTO_THE_PAST = 'DUE_DATE_MOVING_INTO_THE_PAST'

/**
 * El código de una negativa, si la trajo.
 *
 * `details` llega como `Record<string, unknown>` a propósito —las claves
 * cambian por negativa—, así que se pregunta por el código en vez de afirmarlo.
 */
export function refusalCode(result: { details?: Record<string, unknown> }): string | null {
  const code = result.details?.code
  return typeof code === 'string' ? code : null
}

/**
 * La URL del mes anterior o el siguiente, conservando los filtros puestos.
 *
 * El desplazamiento se calcula sobre `since` —la ventana que el backend
 * devolvió— y no sobre la fecha de hoy: el «mes anterior» de lo que se está
 * mirando es coherente con lo que se está mirando, y no con un mes que la
 * pantalla supuso. `Date.UTC` en lugar del constructor local para que la
 * ventana no se corra un día según dónde esté el navegador.
 */
export function windowFor(since: string, offset: number, filters: CalendarFilters): string {
  const [year, month] = since.split('-').map(Number)
  const first = new Date(Date.UTC(year, month - 1 + offset, 1))
  const last = new Date(Date.UTC(year, month + offset, 0))
  const iso = (date: Date) => date.toISOString().slice(0, 10)
  const query = new URLSearchParams({ since: iso(first), until: iso(last) })
  if (filters.sin_recibo) query.set('sin_recibo', filters.sin_recibo)
  if (filters.saldadas) query.set('saldadas', filters.saldadas)
  return `/calendario?${query.toString()}`
}

/** Los días de una semana, de lunes a domingo, en ISO (`aaaa-mm-dd`). */
export type Week = readonly string[]

/** Un día en ISO, desde una fecha en UTC. */
function iso(date: Date): string {
  return date.toISOString().slice(0, 10)
}

/** El mediodía UTC del día que dice un ISO: inmune a cualquier huso. */
function utc(day: string): Date {
  const [year, month, date] = day.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, date, 12))
}

/**
 * La grilla del mes: semanas de lunes a domingo que cubren toda la ventana.
 *
 * Es lo que distingue un calendario de una lista de días con algo. Un día sin
 * vencimientos **existe** en la grilla, vacío, y eso es parte de lo que se viene
 * a ver: dónde no hay nada. Una lista agrupada no puede mostrarlo, porque un
 * día sin entradas no tiene fila.
 *
 * Se extiende hasta el lunes anterior a `since` y el domingo posterior a
 * `until` porque una semana partida al medio deja de leerse como una semana;
 * esos días de relleno se distinguen con `isInWindow`.
 */
export function weeksOf(since: string, until: string): Week[] {
  const cursor = utc(since)
  // `getUTCDay()` numera el domingo como 0: se corre para que la semana empiece
  // el lunes, que es como se lee un mes de trabajo.
  cursor.setUTCDate(cursor.getUTCDate() - ((cursor.getUTCDay() + 6) % 7))
  const last = utc(until)
  last.setUTCDate(last.getUTCDate() + ((7 - last.getUTCDay()) % 7))

  const weeks: Week[] = []
  while (cursor <= last) {
    const week: string[] = []
    for (let index = 0; index < 7; index += 1) {
      week.push(iso(cursor))
      cursor.setUTCDate(cursor.getUTCDate() + 1)
    }
    weeks.push(week)
  }
  return weeks
}

/** Si un día de la grilla pertenece a la ventana que se está mirando. */
export function isInWindow(day: string, since: string, until: string): boolean {
  return day >= since && day <= until
}

/** El número de día, que es lo único que una celda de la grilla escribe. */
export function dayNumber(day: string): string {
  return String(Number(day.slice(8, 10)))
}
