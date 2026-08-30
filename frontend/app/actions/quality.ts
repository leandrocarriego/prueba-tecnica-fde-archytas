'use server'

import { cookies } from 'next/headers'

import type { components } from '@/lib/api/types'

/** What the suite measured, straight from the generated schema. */
export type Quality = components['schemas']['Quality']

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Ask the API how well the code it is running is tested.
 *
 * Behind the session on both sides: the route requires a token, and this page
 * is under `(private)`. `/health` is public and deliberately says nothing about
 * it — how well a system is tested is a fact about the people who build it, not
 * something to be read off the internet by whoever finds the domain.
 *
 * It never throws, and it returns `null` for everything that is not a number:
 * no session, no snapshot in the image, an API that did not answer. The page
 * then says so. What it must never do is show a figure nobody measured.
 */
export async function readQuality(): Promise<Quality | null> {
  const token = (await cookies()).get('access_token')?.value
  if (!token) return null

  try {
    const response = await fetch(`${API_URL}/api/v1/operations/quality`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    })
    if (!response.ok) return null
    const body: unknown = await response.json()
    if (body === null || typeof body !== 'object') return null
    const candidate = body as Record<string, unknown>
    if (typeof candidate.tests !== 'number' || typeof candidate.coverage !== 'number') {
      return null
    }
    return { tests: candidate.tests, coverage: candidate.coverage }
  } catch {
    return null
  }
}
