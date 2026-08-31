/**
 * Reading the corrections a supplier's card carries.
 *
 * The API sends, with every card, the contact fields somebody corrected by
 * hand: what the register had said, what it says now, and whether a later
 * reading of the padrón came back with something else (RF-18, RF-19 de 004).
 *
 * It is the twin of `lib/catalog/corrections.ts` and not an import of it: the
 * two screens read different marks, and a helper shared between them would
 * only be shared until one of the two labels changes.
 */
import type { SupplierCorrectionMark } from '@/lib/purchases/types'

/** Contact fields of a supplier a person may correct, in the words they read. */
export const SUPPLIER_FIELD_LABELS: Record<string, string> = {
  email: 'el correo',
  phone: 'el teléfono',
  payment_term_days: 'el plazo de pago',
}

/** The correction standing on a field of this card, if there is one. */
export function markFor(
  corrections: SupplierCorrectionMark[] | undefined,
  field: string
): SupplierCorrectionMark | undefined {
  return (corrections ?? []).find(correction => correction.field === field)
}

/** Whether the register has come back contradicting a correction (RF-19). */
export function isConflicted(mark: SupplierCorrectionMark | undefined): boolean {
  return mark?.status === 'CONFLICTED'
}
