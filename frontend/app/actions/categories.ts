'use server'

import { revalidatePath } from 'next/cache'
import { cookies } from 'next/headers'

import type { ActionResult } from '@/app/actions/prices'
import type { Category, Rule, UnclassifiedProduct } from '@/lib/catalog/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_PREFIX = '/api/v1'

const UNREACHABLE = 'No se pudo contactar al servidor'
const NO_SESSION = 'La sesión expiró. Iniciá sesión de nuevo'

interface ApiErrorBody {
  error?: { message?: string }
}

async function call<T>(path: string, init: RequestInit): Promise<ActionResult<T>> {
  const token = (await cookies()).get('access_token')?.value
  if (!token) return { ok: false, message: NO_SESSION }
  try {
    const response = await fetch(`${API_URL}${API_PREFIX}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...(init.headers ?? {}),
      },
      cache: 'no-store',
    })
    if (response.status === 204) return { ok: true, data: undefined as T }
    const body = (await response.json()) as T & ApiErrorBody
    if (!response.ok) return { ok: false, message: body.error?.message ?? UNREACHABLE }
    return { ok: true, data: body }
  } catch {
    return { ok: false, message: UNREACHABLE }
  }
}

/** Add a rubro to the list (RF-05 of 008). */
export async function createCategory(name: string): Promise<ActionResult<Category>> {
  const result = await call<Category>('/categories', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
  if (result.ok) revalidatePath('/rubros')
  return result
}

/** Change the name of a rubro (RF-06 of 008). */
export async function renameCategory(
  categoryId: number,
  name: string
): Promise<ActionResult<Category>> {
  const result = await call<Category>(`/categories/${categoryId}`, {
    method: 'PATCH',
    body: JSON.stringify({ name }),
  })
  if (result.ok) revalidatePath('/rubros')
  return result
}

/** Remove a rubro. Refused, with its reason, if anything points at it (RF-07). */
export async function deleteCategory(categoryId: number): Promise<ActionResult<void>> {
  const result = await call<void>(`/categories/${categoryId}`, { method: 'DELETE' })
  if (result.ok) revalidatePath('/rubros')
  return result
}

/**
 * Give a product its rubro (RF-13, RF-15, RF-20 of 008).
 *
 * Confirming the proposal and correcting it are this same call: only the rubro
 * that travels differs, and the system has no reason to tell them apart.
 */
export async function setProductCategory(
  productId: number,
  categoryId: number
): Promise<ActionResult<UnclassifiedProduct>> {
  const result = await call<UnclassifiedProduct>(`/products/${productId}/category`, {
    method: 'PUT',
    body: JSON.stringify({ category_id: categoryId }),
  })
  if (result.ok) {
    revalidatePath('/rubros/sin-clasificar')
    revalidatePath('/rubros')
  }
  return result
}

/**
 * Point an equivalence at another rubro (RF-28, RF-29 of 008).
 *
 * **Nothing goes back to review.** That is the difference from revoking it, and
 * the easiest thing to confuse in this feature: correcting reassigns, revoking
 * returns the products to the queue.
 */
export async function repointAlias(
  ruleId: number,
  categoryId: number
): Promise<ActionResult<Rule>> {
  const result = await call<Rule>(`/triage/rules/${ruleId}`, {
    method: 'PATCH',
    body: JSON.stringify({ decision: { category_id: categoryId } }),
  })
  if (result.ok) {
    revalidatePath('/rubros/equivalencias')
    revalidatePath('/rubros')
  }
  return result
}
