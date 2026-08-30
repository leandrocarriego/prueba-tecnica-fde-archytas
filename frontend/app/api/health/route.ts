import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

import { probeHealth } from '@/lib/health'

/**
 * What the status card re-checks with, from the browser.
 *
 * The browser has no business reaching the backend directly: in the `full`
 * profile the API sits on another host behind the reverse proxy, and CORS is
 * configured for the app's origin only. So the check goes through Next, which
 * is server-side and already knows how to reach it.
 *
 * It asks for a session, and that is the point rather than a formality. Only
 * the frontend is published — the API carries no Traefik router — so this route
 * is the single way the state of the database and of the WhatsApp channel could
 * leave the machine. Leaving it open while the page that uses it requires a
 * session would hide the page and not the answer.
 *
 * The backend's own `/health` stays public and must: the container's healthcheck
 * calls it before anybody logs in, and it is not reachable from outside.
 */

// A cached health check is not a health check.
export const dynamic = 'force-dynamic'

export async function GET(): Promise<NextResponse> {
  if (!(await cookies()).get('access_token')) {
    return NextResponse.json({ error: 'No autorizado' }, { status: 401 })
  }

  const probe = await probeHealth()

  // Always 200, even when the probe failed: what this route reports is the
  // *result of asking*, and the asking succeeded. Answering 503 here would
  // conflate "the API is down" with "this endpoint is down" and leave the page
  // unable to tell the visitor which one happened.
  return NextResponse.json(probe, {
    status: 200,
    headers: { 'Cache-Control': 'no-store' },
  })
}
