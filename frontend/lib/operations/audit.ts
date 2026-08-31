/**
 * Reading a line of the history in the words the team uses.
 *
 * The backend stores what a change did as an enum and what it touched as the
 * publishing module's own string (`catalog.product_price`). Neither is meant
 * for a person, and translating them is a rendering concern: nothing here is a
 * rule, so nothing here can drift away from one.
 */
import type { AuditAction, AuditEntry } from '@/lib/operations/types'

/**
 * The word this screen reads for each action the backend records.
 *
 * A `Map`, like the two below and for the same reason: every key looked up in
 * this file arrives from outside — the API, or the address bar — and an object
 * answers `constructor` or `toString` with something inherited that is not a
 * label at all, which the `??` fallbacks below would then hand to the screen
 * as if it were one.
 *
 * The entries are still written as a record so `satisfies` can demand all of
 * them: these keys are the whole enum, so an action added to the backend has
 * to break the build here instead of reaching the screen as `MERGED`.
 */
const ACTIONS = new Map<string, string>(
  Object.entries({
    CREATED: 'Cargó',
    UPDATED: 'Modificó',
    CORRECTED: 'Corrigió',
    CORRECTION_REVERTED: 'Deshizo una corrección',
  } satisfies Record<AuditAction, string>)
)

/** The kinds of datum this screen has a word for. Every feature adds its line. */
const ENTITIES = new Map<string, string>([
  ['operations.parameter', 'Parámetro del sistema'],
  ['catalog.product', 'Producto'],
  ['catalog.product_price', 'Precio'],
])

const FIELDS = new Map<string, string>([
  ['price', 'precio'],
  ['currency', 'moneda'],
  ['description', 'descripción'],
])

/** What the change did, in one word. */
export function actionLabel(action: AuditAction): string {
  return ACTIONS.get(action) ?? action
}

/**
 * What kind of datum it touched.
 *
 * A kind with no line in `ENTITIES` is a gap in this screen's vocabulary, not
 * an ordinary row, and it is neither hidden nor shown raw. Raw is jargon the
 * owner never asked for — `purchases.supplier`, which the backend already
 * writes, on a screen in Spanish (`TS-09`) — and hiding it would make two
 * different kinds of datum read the same, in a log whose whole job is letting
 * a number be explained afterwards.
 * So it is named in Spanish and keeps its technical key, which is also what
 * makes the missing line visible to whoever has to add it.
 */
export function entityLabel(entityType: string): string {
  return ENTITIES.get(entityType) ?? `Otro dato (${entityType})`
}

/**
 * Which field, when the change was to one field and not to the whole record.
 *
 * Same decision as `entityLabel`, in lower case because the row reads it right
 * after one: which field changed survives even when its name does not.
 */
export function fieldLabel(field: string | null): string | null {
  if (field === null) return null
  return FIELDS.get(field) ?? `otro campo (${field})`
}

/**
 * Whether this is a kind of datum the screen knows by name.
 *
 * The history of a single datum is asked for through the address bar
 * (`?entidad=…&id=…`), so the kind is text anybody can type. It is not cleaned,
 * it is *matched* — and against the kinds this screen can name, not against
 * everything that exists: `purchases.supplier` is written by the backend
 * today, and until the feature that writes it adds its line above it is
 * answered here the same as a typo. Which is the honest answer while it lasts,
 * because the screen has no word for it either, and a different answer from
 * "no hubo cambios", so it has to be said differently. A feature that starts
 * linking here adds its line above, the same line that gives it a label.
 */
export function isKnownEntityType(entityType: string): boolean {
  return ENTITIES.has(entityType)
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
