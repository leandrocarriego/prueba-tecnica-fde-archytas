import { NextResponse } from 'next/server'

import { probeHealth } from '@/lib/health'

/**
 * Public, unauthenticated counterpart of `app/api/proxy/[...path]`.
 *
 * That one exists to attach a session token; this one exists precisely because
 * there is none. The status page needs to re-check the API from the browser,
 * and the browser has no business reaching the backend directly: in the `full`
 * profile the API is behind the reverse proxy on another host, and CORS is
 * configured for the app's origin only. So the check goes through Next, which
 * is server-side and already knows how to reach the backend.
 */

// A cached health check is not a health check.
export const dynamic = 'force-dynamic'

export async function GET(): Promise<NextResponse> {
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
