/**
 * Notifications types, derived from the generated OpenAPI schema.
 *
 * Aliases y no interfaces escritas a mano, como en todos los módulos: el
 * backend es la fuente del contrato y un rename allá tiene que romper el build
 * acá.
 */
import type { components } from '@/lib/api/types'

export type AlertKind = components['schemas']['AlertKind']
export type AlertRoute = components['schemas']['RouteRead']

/**
 * Qué es cada tipo de aviso, dicho como lo diría quien lo recibe (RF-37).
 *
 * El backend manda la clave; el nombre que se lee en la pantalla vive acá
 * porque es un string de UI y va en español.
 */
export const ALERT_KINDS: Record<AlertKind, string> = {
  PAYMENT_CLAIM: 'Reclamo de pago de un proveedor',
  DUE_SOON: 'Aviso de algo que está por vencer',
  DAILY_DIGEST: 'Resumen diario de lo que quedó abierto',
}

/**
 * Los dos roles que pueden recibir un aviso.
 *
 * Ventas no está, y no es una omisión: RF-46 dice que ventas no llega a la
 * bandeja de mensajes de la que hablan estos avisos. El endpoint acepta
 * exactamente estos dos, así que la lista no es una cortesía de la pantalla.
 */
export const ALERT_ROLES: Record<string, string> = {
  OWNER: 'El dueño',
  PURCHASING: 'Compras',
}
