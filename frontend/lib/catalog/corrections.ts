/**
 * Reading the corrections a row carries.
 *
 * The API sends, with every product, the fields somebody corrected by hand:
 * what the portal had said, what it says now, and whether the portal has since
 * come back with something else. These are the two helpers every screen that
 * shows them needs, so the phrase a person reads is written once.
 */
import type { CorrectionMark } from '@/lib/catalog/types'

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
