'use server'

import { revalidatePath } from 'next/cache'

import type { ActionResult } from '@/app/actions/prices'
import type { Case } from '@/lib/triage/types'

import { cookies } from 'next/headers'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_PREFIX = '/api/v1'

const UNREACHABLE = 'No se pudo contactar al servidor'
const NO_SESSION = 'La sesión expiró. Iniciá sesión de nuevo'

interface ApiErrorBody {
  error?: { type?: string; message?: string }
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
 * Decide what to do with a case (RF-29 to RF-33).
 *
 * `remember` is on by default, which is Artículo II: the decision is kept as a
 * rule so the same question is not asked again tomorrow.
 */
export async function resolveCase(
  caseId: number,
  decision: Record<string, unknown>,
  remember = true
): Promise<ActionResult<Case>> {
  const result = await call<Case>(`/triage/cases/${caseId}/resolution`, {
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
  const result = await call<void>(`/triage/rules/${ruleId}`, { method: 'DELETE' })
  if (result.ok) {
    revalidatePath('/revision')
    revalidatePath('/precios')
  }
  return result
}
