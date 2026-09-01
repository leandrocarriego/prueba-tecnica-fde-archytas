'use server'

import { revalidatePath } from 'next/cache'
import { cookies } from 'next/headers'

import type { ActionResult } from '@/app/actions/prices'
import type { Sale } from '@/lib/sales/types'

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

/**
 * Decide about a repeated sale (RF-31, RF-32 of 009).
 *
 * `keep` chooses which version is valid and keeps the other visible beside it;
 * `distinct` declares that they were never the same sale.
 */
export async function resolveSaleGroup(
  codeKey: string,
  action: 'keep' | 'distinct',
  saleId: number | null
): Promise<ActionResult<Sale[]>> {
  const result = await call<Sale[]>(`/sales/groups/${encodeURIComponent(codeKey)}/resolution`, {
    method: 'POST',
    body: JSON.stringify({ action, sale_id: saleId }),
  })
  if (result.ok) {
    revalidatePath('/revision')
    revalidatePath('/ventas')
    revalidatePath('/tablero')
  }
  return result
}

/** Undo a decision and recalculate the indicators with it (RF-35 of 009). */
export async function undoSaleResolution(codeKey: string): Promise<ActionResult<Sale[]>> {
  const result = await call<Sale[]>(`/sales/groups/${encodeURIComponent(codeKey)}/resolution`, {
    method: 'DELETE',
  })
  if (result.ok) {
    revalidatePath('/revision')
    revalidatePath('/ventas')
    revalidatePath('/tablero')
  }
  return result
}

/**
 * Correct a held sale, or estimate what cannot be known (RF-38, RF-39 of 009).
 *
 * What the portal reported is kept whatever is corrected, and a value the
 * person estimated is marked so every indicator built on it says so.
 */
export async function correctSale(
  saleId: number,
  values: {
    sold_on?: string | null
    product_code?: string | null
    quantity?: number | null
    total?: string | null
  },
  isEstimated = false
): Promise<ActionResult<Sale>> {
  const result = await call<Sale>(`/sales/${saleId}`, {
    method: 'PATCH',
    body: JSON.stringify({ ...values, is_estimated: isEstimated }),
  })
  if (result.ok) {
    revalidatePath('/revision')
    revalidatePath('/ventas')
    revalidatePath('/tablero')
  }
  return result
}
