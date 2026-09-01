'use server'

/**
 * Server Actions for the access screens.
 *
 * Everything here goes through the API with the caller's own session, so the
 * backend decides what is allowed. Nothing in this file re-implements a rule:
 * if the owner is the only one who may hand out an access, it is because the
 * route says so — these actions would get a 403 like anybody else.
 */

import { revalidatePath } from 'next/cache'
import { cookies } from 'next/headers'

import type { components } from '@/lib/api/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export type UserRead = components['schemas']['UserRead']
export type UserList = components['schemas']['UserList']
export type AccessEventList = components['schemas']['AccessEventList']
export type UserRole = components['schemas']['UserRole']

/** What a screen gets back: what happened, in words a person can read. */
export interface ActionResult {
  ok: boolean
  message: string
}

interface ApiErrorBody {
  error?: { type?: string; message?: string }
}

async function authorized(): Promise<HeadersInit> {
  const token = (await cookies()).get('access_token')?.value
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

/** Turn a failing response into the sentence the screen shows. */
async function failure(response: Response, fallback: string): Promise<ActionResult> {
  if (response.status === 403) {
    return { ok: false, message: 'No tenés permiso para hacer esto.' }
  }
  try {
    const body = (await response.json()) as ApiErrorBody
    return { ok: false, message: body.error?.message || fallback }
  } catch {
    return { ok: false, message: fallback }
  }
}

// --- Reading -------------------------------------------------------------

/** The accesses the owner administers. Null means the caller may not see them. */
export async function listAccesses(): Promise<UserList | null> {
  const response = await fetch(`${API_URL}/api/v1/users?limit=200`, {
    headers: await authorized(),
    cache: 'no-store',
  })
  return response.ok ? ((await response.json()) as UserList) : null
}

/** The record of who came in and who was turned away. */
export async function listAccessEvents(kind?: string): Promise<AccessEventList | null> {
  const query = kind ? `?limit=100&kind=${encodeURIComponent(kind)}` : '?limit=100'
  const response = await fetch(`${API_URL}/api/v1/access-log${query}`, {
    headers: await authorized(),
    cache: 'no-store',
  })
  return response.ok ? ((await response.json()) as AccessEventList) : null
}

// --- Administering -------------------------------------------------------

export async function createAccess(formData: FormData): Promise<ActionResult> {
  const payload = {
    email: String(formData.get('email') || ''),
    name: String(formData.get('name') || ''),
    last_name: String(formData.get('last_name') || '') || null,
    phone: String(formData.get('phone') || ''),
    role: String(formData.get('role') || 'SALES'),
  }

  const response = await fetch(`${API_URL}/api/v1/users`, {
    method: 'POST',
    headers: await authorized(),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    return failure(response, 'No se pudo dar de alta el acceso.')
  }
  revalidatePath('/configuracion/accesos')
  return {
    ok: true,
    // Says where the invitation went, because that is the next thing that has
    // to happen and nobody can do it from here.
    message: `Acceso creado. La invitación salió por WhatsApp al ${payload.phone}.`,
  }
}

export async function changeRole(userId: number, role: string): Promise<ActionResult> {
  const response = await fetch(`${API_URL}/api/v1/users/${userId}`, {
    method: 'PATCH',
    headers: await authorized(),
    body: JSON.stringify({ role }),
  })

  if (!response.ok) {
    return failure(response, 'No se pudo cambiar el rol.')
  }
  revalidatePath('/configuracion/accesos')
  return { ok: true, message: 'Rol cambiado. Se aplica la próxima vez que entre.' }
}

export async function deactivateAccess(userId: number): Promise<ActionResult> {
  const response = await fetch(`${API_URL}/api/v1/users/${userId}/deactivate`, {
    method: 'POST',
    headers: await authorized(),
  })

  if (!response.ok) {
    return failure(response, 'No se pudo desactivar el acceso.')
  }
  revalidatePath('/configuracion/accesos')
  return { ok: true, message: 'Acceso desactivado. Sus sesiones abiertas se cerraron.' }
}

export async function reactivateAccess(userId: number): Promise<ActionResult> {
  const response = await fetch(`${API_URL}/api/v1/users/${userId}/reactivate`, {
    method: 'POST',
    headers: await authorized(),
  })

  if (!response.ok) {
    return failure(response, 'No se pudo reactivar el acceso.')
  }
  revalidatePath('/configuracion/accesos')
  return {
    ok: true,
    message: 'Acceso reactivado. Le llegó una invitación para definir una clave nueva.',
  }
}

// --- One's own credential ------------------------------------------------

export async function changeOwnPassword(formData: FormData): Promise<ActionResult> {
  const current = String(formData.get('current_password') || '')
  const next = String(formData.get('new_password') || '')
  const repeat = String(formData.get('repeat_password') || '')

  if (next !== repeat) {
    return { ok: false, message: 'La clave nueva y su repetición no coinciden.' }
  }

  const response = await fetch(`${API_URL}/api/v1/auth/password/change`, {
    method: 'POST',
    headers: await authorized(),
    body: JSON.stringify({ current_password: current, new_password: next }),
  })

  if (!response.ok) {
    return failure(response, 'No se pudo cambiar la clave.')
  }
  return {
    ok: true,
    message: 'Clave cambiada. Las sesiones abiertas en otros navegadores se cerraron.',
  }
}

/** Ask for a recovery link. Answers the same whether or not the address exists. */
export async function requestRecovery(formData: FormData): Promise<ActionResult> {
  const email = String(formData.get('email') || '')
  await fetch(`${API_URL}/api/v1/auth/password-reset/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  // Deliberately the same sentence in every case: telling somebody that an
  // address is not registered turns this form into a way of finding out who
  // has an account.
  return {
    ok: true,
    message: 'Si ese correo corresponde a un acceso, el enlace ya salió por WhatsApp.',
  }
}

/** Redeem an invitation or a recovery link by setting a password. */
export async function setPasswordWithToken(
  kind: 'invitacion' | 'recuperar',
  token: string,
  formData: FormData
): Promise<ActionResult> {
  const next = String(formData.get('new_password') || '')
  const repeat = String(formData.get('repeat_password') || '')

  if (next !== repeat) {
    return { ok: false, message: 'La clave y su repetición no coinciden.' }
  }

  const path = kind === 'invitacion' ? 'invitation' : 'password-reset'
  const response = await fetch(`${API_URL}/api/v1/auth/${path}/${encodeURIComponent(token)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_password: next }),
  })

  if (!response.ok) {
    return failure(response, 'El enlace no sirve: puede haber vencido o haberse usado ya.')
  }
  return { ok: true, message: 'Listo. Ya podés entrar con tu clave nueva.' }
}

/** Whether a link still works, so the screen can say so before asking for a password. */
export async function tokenIsUsable(
  kind: 'invitacion' | 'recuperar',
  token: string
): Promise<boolean> {
  const path = kind === 'invitacion' ? 'invitation' : 'password-reset'
  const response = await fetch(`${API_URL}/api/v1/auth/${path}/${encodeURIComponent(token)}`, {
    cache: 'no-store',
  })
  if (!response.ok) {
    return false
  }
  const body = (await response.json()) as { usable?: boolean }
  return Boolean(body.usable)
}
