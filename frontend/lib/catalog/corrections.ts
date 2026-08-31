/**
 * Reading the corrections a row carries.
 *
 * The API sends, with every product, the fields somebody corrected by hand:
 * what the portal had said, what it says now, and whether the portal has since
 * come back with something else. These are the helpers every screen that shows
 * them needs, so the phrase a person reads is written once.
 *
 * The last two are for a screen that is **not** the datum's own page — the
 * change log, which lists corrections of many data at once and has to tell
 * which correction stands on which row before it can offer to undo it (RF-30).
 */
import type { CorrectionInForce, CorrectionMark } from '@/lib/catalog/types'

/** Fields of a product a person may correct, in the words they read. */
export const FIELD_LABELS: Record<string, string> = {
  price: 'el precio',
  currency: 'la moneda',
  description: 'la descripción',
}

/**
 * The same fields with no article, for the phrases that already carry one.
 *
 * Two maps and not one `.slice()` over the first: dropping the article by
 * cutting the string works in Spanish until the day a field is named by two
 * words, and a label the user reads is not the place to find that out.
 */
export const FIELD_NOUNS: Record<string, string> = {
  price: 'precio',
  currency: 'moneda',
  description: 'descripción',
}

/** The correction standing on a field of this row, if there is one. */
export function markFor(corrections: CorrectionMark[], field: string): CorrectionMark | undefined {
  return corrections.find(correction => correction.field === field)
}

/** Whether the portal has come back contradicting a correction (RF-28). */
export function isConflicted(mark: CorrectionMark | undefined): boolean {
  return mark?.status === 'CONFLICTED'
}

/**
 * The three things that name a datum, as one key.
 *
 * The change log and the corrections endpoint say the same thing in the same
 * words — `catalog.product_price`, the product id as text, the field — so a row
 * of one is matched against a row of the other without either side learning the
 * other's shape. Built here rather than in the screen so both callers key it
 * identically: a key written twice is a lookup that silently misses.
 */
export function datumKey(entityType: string, entityId: string, field: string | null): string {
  return `${entityType}|${entityId}|${field ?? ''}`
}

/**
 * Which correction stands on which datum, keyed for a screen that lists many.
 *
 * What the change log needs to offer the undo beside a row (RF-30): the row
 * says a value was corrected, and this says which correction that is — or
 * nothing, if it was already undone, in which case there is no offer to make.
 */
export function standingCorrections(corrections: CorrectionInForce[]): Map<string, number> {
  return new Map(
    corrections.map(correction => [
      datumKey(correction.entity_type, correction.entity_id, correction.field),
      correction.correction_id,
    ])
  )
}
