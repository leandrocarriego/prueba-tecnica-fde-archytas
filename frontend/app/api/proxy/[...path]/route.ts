import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_PREFIX = 'api/v1'

type RouteParams = { params: Promise<{ path: string[] }> }

/**
 * Proxy for every browser call to the FastAPI backend.
 *
 * It exists so the access token can live in an httpOnly cookie: the browser
 * never sees it, and this handler is what turns that cookie into the
 * `Authorization: Bearer` header the backend expects. A `rewrites()` entry in
 * next.config could not do that, and would leave the backend reachable without
 * authentication.
 */
export async function GET(request: NextRequest, { params }: RouteParams) {
  const { path } = await params
  return handleRequest(request, path, 'GET')
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  const { path } = await params
  return handleRequest(request, path, 'POST')
}

export async function PUT(request: NextRequest, { params }: RouteParams) {
  const { path } = await params
  return handleRequest(request, path, 'PUT')
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  const { path } = await params
  return handleRequest(request, path, 'DELETE')
}

export async function PATCH(request: NextRequest, { params }: RouteParams) {
  const { path } = await params
  return handleRequest(request, path, 'PATCH')
}

/** Build the error envelope the backend uses, so callers only parse one shape. */
function errorResponse(type: string, message: string, status: number) {
  return NextResponse.json({ error: { type, message, details: {} } }, { status })
}

async function handleRequest(request: NextRequest, pathArray: string[], method: string) {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get('access_token')?.value

    if (!token) {
      return errorResponse('Unauthorized', 'No autenticado', 401)
    }

    // Callers may or may not include the API prefix; accept both.
    let path = pathArray.join('/')
    if (!path.startsWith(API_PREFIX)) {
      path = `${API_PREFIX}/${path}`
    }

    const queryString = new URL(request.url).search

    const headers: HeadersInit = { Authorization: `Bearer ${token}` }

    let body: string | undefined
    if (['POST', 'PUT', 'PATCH'].includes(method)) {
      try {
        body = JSON.stringify(await request.json())
        headers['Content-Type'] = 'application/json'
      } catch {
        // No body sent: leave it undefined and do not claim a JSON content type.
      }
    }

    const response = await fetch(`${API_URL}/${path}${queryString}`, {
      method,
      headers,
      body,
    })

    // Not every response carries JSON. A 204 (password change, user
    // deactivation) has no body at all, and parsing it unconditionally used to
    // turn a successful call into a generic 500.
    if (response.status === 204) {
      return new NextResponse(null, { status: 204 })
    }

    const contentType = response.headers.get('content-type') ?? ''
    if (!contentType.includes('application/json')) {
      const text = await response.text()
      return new NextResponse(text, {
        status: response.status,
        headers: contentType ? { 'Content-Type': contentType } : undefined,
      })
    }

    return NextResponse.json(await response.json(), { status: response.status })
  } catch (error) {
    // The backend is unreachable or answered something unparseable: that is a
    // gateway problem, not an application error.
    console.error('Proxy error:', error)
    return errorResponse('BadGateway', 'No se pudo contactar al servidor', 502)
  }
}
