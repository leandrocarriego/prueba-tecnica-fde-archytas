'use server'

import { revalidatePath } from 'next/cache'

import { callApi, type ActionResult } from '@/lib/api/write'
import type { Correction } from '@/lib/catalog/types'

interface CorrectionInput {
  productId: number
  field: string
  value: string
  reasonCode: string
  reasonDetail?: string
}

/**
 * Correct a value of a product by hand (RF-11, RF-23, RF-25).
 *
 * The reason travels with the value because the backend refuses the correction
 * without one — which is the point: a correction with no reason is a number
 * that appeared.
 */
export async function correctProduct({
  productId,
  field,
  value,
  reasonCode,
  reasonDetail,
}: CorrectionInput): Promise<ActionResult<Correction>> {
  const result = await callApi<Correction>(`/catalog/products/${productId}/corrections`, {
    method: 'POST',
    body: JSON.stringify({
      field,
      value,
      reason_code: reasonCode,
      reason_detail: reasonDetail?.trim() ? reasonDetail.trim() : null,
    }),
  })
  if (result.ok) {
    revalidatePath('/precios')
    revalidatePath(`/precios/${productId}`)
    revalidatePath('/historial')
  }
  return result
}

/**
 * Undo a correction, giving the datum back the portal's value (RF-30, RF-31).
 *
 * Owner-only on the backend, so this fails cleanly for anybody else — and the
 * screens that offer it only do so where there is a correction to undo, which
 * is what RF-33 asks for.
 */
export async function revertCorrection(correctionId: number): Promise<ActionResult<Correction>> {
  const result = await callApi<Correction>(`/catalog/corrections/${correctionId}`, {
    method: 'DELETE',
  })
  if (result.ok) {
    revalidatePath('/precios')
    revalidatePath(`/precios/${result.data.product_id}`)
    revalidatePath('/historial')
  }
  return result
}
