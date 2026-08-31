'use server'

import { revalidatePath } from 'next/cache'

import { callApi, type ActionResult } from '@/lib/api/write'
import type { Case } from '@/lib/triage/types'

/**
 * The review queue's two write actions.
 *
 * They used to go through a copy of the API client kept in this file, from
 * before `lib/api/write` existed. The copy has been dropped: it had drifted —
 * its own `ApiErrorBody` did not even declare `details` — and a refusal that
 * arrives without them is a message the screen can print and not act on, which
 * is exactly what resolving a case needs (RF-22).
 */

/**
 * Decide what to do with a case (RF-29 to RF-33).
 *
 * `remember` is on by default, which is Artículo II: the decision is kept as a
 * rule so the same question is not asked again tomorrow.
 *
 * A refusal revalidates nothing on purpose. Nothing moved — the backend aborts
 * the whole resolution when what the person decided cannot be applied — and
 * refreshing the queue would take the card, and its explanation, off the screen.
 */
export async function resolveCase(
  caseId: number,
  decision: Record<string, unknown>,
  remember = true
): Promise<ActionResult<Case>> {
  const result = await callApi<Case>(`/triage/cases/${caseId}/resolution`, {
    method: 'POST',
    body: JSON.stringify({ decision, remember }),
  })
  if (result.ok) {
    revalidatePath('/revision')
    revalidatePath('/precios')
  }
  return result
}

/** Leave a rule without effect, and give its cases back (RF-37). */
export async function revokeRule(ruleId: number): Promise<ActionResult<void>> {
  const result = await callApi<void>(`/triage/rules/${ruleId}`, { method: 'DELETE' })
  if (result.ok) {
    revalidatePath('/revision')
    revalidatePath('/precios')
  }
  return result
}
