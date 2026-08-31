import { cookies } from 'next/headers'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Un stream que no termina no se puede pre-renderizar ni cachear.
export const dynamic = 'force-dynamic'

/**
 * El canal en vivo del calendario, entre el navegador y la API.
 *
 * Existe por una razón concreta y no por simetría con `/api/proxy`: el token de
 * sesión vive en una cookie que sólo lee el servidor, y `EventSource` **no
 * puede mandar headers**. Sin este handler, la única forma de autenticar el
 * stream sería pasar el token por la query string, que es donde terminan los
 * tokens de los tutoriales de SSE y también los logs de acceso de cualquier
 * proxy intermedio.
 *
 * Y no se puede usar el proxy general: ese lee `arrayBuffer()`, que espera a
 * que la respuesta **termine**. Un stream no termina, así que ahí se colgaría
 * para siempre. Acá el cuerpo se pasa tal cual, sin tocarlo.
 */
export async function GET() {
  const token = (await cookies()).get('access_token')?.value
  if (!token) {
    return new Response('No autenticado', { status: 401 })
  }

  let upstream: Response
  try {
    upstream = await fetch(`${API_URL}/api/v1/calendar/stream`, {
      headers: { Authorization: `Bearer ${token}`, Accept: 'text/event-stream' },
      cache: 'no-store',
    })
  } catch {
    // La API no contesta. Se devuelve un error y el navegador reintenta solo,
    // que es exactamente lo que RF-36 pide que pase al restablecerse.
    return new Response('El canal no está disponible', { status: 502 })
  }

  if (!upstream.ok || upstream.body === null) {
    return new Response('El canal no está disponible', { status: upstream.status || 502 })
  }

  return new Response(upstream.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      // Nginx bufferea por defecto y un stream buffereado no es un stream.
      'X-Accel-Buffering': 'no',
    },
  })
}
