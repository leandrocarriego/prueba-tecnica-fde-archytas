/**
 * Reading a line of the history in the words the team uses.
 *
 * The backend stores what a change did as an enum and what it touched as the
 * publishing module's own string (`catalog.product_price`). Neither is meant
 * for a person, and translating them is a rendering concern: nothing here is a
 * rule, so nothing here can drift away from one.
 */
import type { AuditAction, AuditEntry } from '@/lib/operations/types'

const ACTIONS: Record<AuditAction, string> = {
  CREATED: 'Cargó',
  UPDATED: 'Modificó',
  CORRECTED: 'Corrigió',
  CORRECTION_REVERTED: 'Deshizo una corrección',
}

const ENTITIES: Record<string, string> = {
  'operations.parameter': 'Parámetro del sistema',
  'catalog.product': 'Producto',
  'catalog.product_price': 'Precio',
}

const FIELDS: Record<string, string> = {
  price: 'precio',
  currency: 'moneda',
  description: 'descripción',
}

/** What the change did, in one word. */
export function actionLabel(action: AuditAction): string {
  return ACTIONS[action] ?? action
}

/** What kind of datum it touched. An unknown kind answers with its own name. */
export function entityLabel(entityType: string): string {
  return ENTITIES[entityType] ?? entityType
}

/** Which field, when the change was to one field and not to the whole record. */
export function fieldLabel(field: string | null): string | null {
  return field === null ? null : (FIELDS[field] ?? field)
}

/**
 * A stored value, as text.
 *
 * Values travel as JSON because one column has to hold a price, a date and a
 * description. `—` for the ends that are genuinely empty: a creation has no
 * previous value, and that is not the same as an empty one.
 */
export function valueText(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return JSON.stringify(value)
}

/** Where the datum of an entry lives, when it has a screen of its own (RF-15). */
export function entityHref(entry: AuditEntry): string | null {
  if (entry.entity_type === 'catalog.product' || entry.entity_type === 'catalog.product_price') {
    return `/precios/${entry.entity_id}`
  }
  if (entry.entity_type === 'operations.parameter') return '/configuracion'
  return null
}
