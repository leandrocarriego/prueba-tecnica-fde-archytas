'use server'

import { revalidatePath } from 'next/cache'
import { cookies } from 'next/headers'

import type { ActionResult } from '@/app/actions/prices'
import type { Message } from '@/lib/messaging/types'

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

/** Mark a message as dealt with (RF-28, RF-29 of 007). */
export async function resolveMessage(messageId: number): Promise<ActionResult<Message>> {
  const result = await call<Message>(`/messages/${messageId}/resolution`, { method: 'POST' })
  if (result.ok) revalidatePath('/mensajes')
  return result
}

/** Say who is responsible for a message (RF-30 of 007). */
export async function assignMessage(
  messageId: number,
  assigneeUserId: number | null
): Promise<ActionResult<Message>> {
  const result = await call<Message>(`/messages/${messageId}/assignee`, {
    method: 'PUT',
    body: JSON.stringify({ assignee_user_id: assigneeUserId }),
  })
  if (result.ok) revalidatePath('/mensajes')
  return result
}

/** Write a note on a message (RF-32 of 007). */
export async function annotateMessage(
  messageId: number,
  note: string
): Promise<ActionResult<Message>> {
  const result = await call<Message>(`/messages/${messageId}/note`, {
    method: 'POST',
    body: JSON.stringify({ note }),
  })
  if (result.ok) revalidatePath('/mensajes')
  return result
}
