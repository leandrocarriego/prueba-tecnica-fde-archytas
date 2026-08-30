import type { components } from '@/lib/api/types'

/** The body `/api/v1/health` answers with, straight from the generated schema. */
type WireHealth = components['schemas']['HealthRead']

/**
 * What actually crosses to the browser.
 *
 * Every field is typed *from* the generated schema, so a change in the backend
 * still breaks this at compile time rather than rendering `undefined` in front
 * of a visitor. What it drops is `database.detail`: the backend writes it in
 * English for operators, this page is public and Spanish, and the card does not
 * show it. A field nothing renders has no reason to be serialised into the HTML
 * of a page anyone can open.
 */
export type HealthReport = {
  status: WireHealth['status']
  service: WireHealth['service']
  environment: WireHealth['environment']
  database: { status: WireHealth['database']['status'] }
  whatsapp: { status: WireHealth['whatsapp']['status'] }
}

/**
 * The outcome of one probe.
 *
 * `reachable` describes the HTTP conversation, not the health of the platform.
 * The API answers **503 with a perfectly valid report** when its database is
 * down — that is an answer, and the page has something real to show. Only a
 * request that never produced a usable body is `reachable: false`.
 */
export type HealthProbe =
  | { reachable: true; httpStatus: number; report: HealthReport }
  | { reachable: false; reason: string }

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const HEALTH_PATH = '/api/v1/health'

/** A health check that hangs is a health check that failed. */
const TIMEOUT_MS = 5_000

/** Narrow an unknown JSON body to the wire shape before trusting any of it. */
function isWireHealth(value: unknown): value is WireHealth {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as Record<string, unknown>
  const database = candidate.database as Record<string, unknown> | null | undefined
  const whatsapp = candidate.whatsapp as Record<string, unknown> | null | undefined
  return (
    isState(candidate.status) &&
    typeof candidate.service === 'string' &&
    typeof candidate.environment === 'string' &&
    typeof database === 'object' &&
    database !== null &&
    isState(database.status) &&
    typeof whatsapp === 'object' &&
    whatsapp !== null &&
    isState(whatsapp.status)
  )
}

function isState(value: unknown): value is WireHealth['status'] {
  return value === 'ok' || value === 'down' || value === 'off'
}

/** Keep only the fields the page renders. */
function toReport(wire: WireHealth): HealthReport {
  return {
    status: wire.status,
    service: wire.service,
    environment: wire.environment,
    database: { status: wire.database.status },
    whatsapp: { status: wire.whatsapp.status },
  }
}

/**
 * Ask the API how it is doing. Runs on the server (Server Component and route
 * handler), never in the browser: the backend is not necessarily reachable from
 * a visitor's network, and on a public page there is no session to borrow.
 *
 * It never throws. A status page whose own render crashes reports nothing.
 */
export async function probeHealth(): Promise<HealthProbe> {
  try {
    const response = await fetch(`${API_URL}${HEALTH_PATH}`, {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(TIMEOUT_MS),
    })

    const body: unknown = await response.json().catch(() => null)

    if (!isWireHealth(body)) {
      return {
        reachable: false,
        reason: `La API respondió ${response.status}, pero con un cuerpo que no se pudo interpretar.`,
      }
    }

    return { reachable: true, httpStatus: response.status, report: toReport(body) }
  } catch (error) {
    return { reachable: false, reason: describeFailure(error) }
  }
}

/**
 * Turn a fetch failure into something a person can act on.
 *
 * Deliberately generic: this page is public, so the message must not leak
 * hostnames, ports or driver details — the same reason the backend keeps
 * `ComponentHealth.detail` vague.
 */
function describeFailure(error: unknown): string {
  if (error instanceof DOMException && error.name === 'TimeoutError') {
    return `La API no respondió en ${TIMEOUT_MS / 1000} segundos.`
  }
  return 'No se pudo establecer conexión con la API.'
}
