'use server'

import { revalidatePath } from 'next/cache'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

import type { components } from '@/lib/api/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type LoginResponse = components['schemas']['LoginResponse']
type UserRead = components['schemas']['UserRead']
/** Who is working plus what they may reach: the shape `/auth/me` answers with. */
export type CurrentSession = components['schemas']['CurrentUser']

/** The envelope every failing endpoint returns: see `app.main` in the backend. */
interface ApiErrorBody {
  error?: { type?: string; message?: string; details?: Record<string, unknown> }
}

type LoginBody = Partial<LoginResponse> & ApiErrorBody

export async function loginAction(formData: FormData) {
  const email = formData.get('email') as string
  const password = formData.get('password') as string
  const remember = formData.get('remember') === 'on'

  if (!email || !password) {
    // Retornar error usando redirect con query param
    redirect('/login?error=' + encodeURIComponent('Email y contraseña son requeridos'))
  }

  try {
    const response = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })

    // Intentar parsear JSON, pero manejar errores si la respuesta no es JSON
    let data: LoginBody = {}
    const contentType = response.headers.get('content-type')
    if (contentType && contentType.includes('application/json')) {
      try {
        data = await response.json()
      } catch {
        // The body claimed to be JSON but is not: surface the raw text.
        const text = await response.text()
        redirect(
          '/login?error=' + encodeURIComponent('Error al iniciar sesión: ' + text.substring(0, 100))
        )
      }
    } else {
      // Si no es JSON, leer como texto
      const text = await response.text()
      redirect(
        '/login?error=' + encodeURIComponent('Error al iniciar sesión: ' + text.substring(0, 100))
      )
    }

    if (!response.ok) {
      // Retornar error usando redirect con query param
      redirect(
        '/login?error=' + encodeURIComponent(data.error?.message || 'Error al iniciar sesión')
      )
    }

    // Guardar token en httpOnly cookie
    const cookieStore = await cookies()
    // Si "recordarme" está marcado, la cookie dura 30 días, sino 30 minutos
    const maxAge = remember ? 30 * 24 * 60 * 60 : 30 * 60 // 30 días o 30 minutos

    if (!data.access_token) {
      redirect('/login?error=' + encodeURIComponent('El servidor no devolvió un token de acceso'))
    }

    cookieStore.set('access_token', data.access_token, {
      httpOnly: true, // ✅ Prevenir acceso desde JavaScript (protección contra XSS)
      secure: process.env.NODE_ENV === 'production', // ✅ Solo HTTPS en producción (protección contra sniffing)
      sameSite: 'lax', // ⚖️ Balance entre seguridad y funcionalidad
      // "strict" sería más seguro pero rompe redirects desde emails/links externos
      // "lax" permite redirects GET cross-site pero bloquea POST/forms (recomendado por OWASP)
      maxAge,
      path: '/', // ✅ Cookie disponible en toda la aplicación
    })

    // Revalidar todos los paths para asegurar que la cookie esté disponible
    // IMPORTANTE: revalidatePath debe ejecutarse ANTES del redirect
    revalidatePath('/', 'layout')
    revalidatePath('/login', 'page')

    // Hacer redirect desde el servidor después de establecer la cookie
    // Esto asegura que la cookie esté disponible cuando se ejecute el layout
    redirect('/')
  } catch (error) {
    // Si es una excepción de redirect, relanzarla
    if (
      error &&
      typeof error === 'object' &&
      'digest' in error &&
      typeof error.digest === 'string' &&
      error.digest.startsWith('NEXT_REDIRECT')
    ) {
      throw error
    }
    console.error('Login error:', error)
    redirect('/login?error=' + encodeURIComponent('Error interno del servidor'))
  }
}

export async function logoutAction() {
  const cookieStore = await cookies()
  const token = cookieStore.get('access_token')?.value

  // Close the session on the server before dropping the cookie. A session is a
  // row now, so forgetting the token client-side would leave it open until it
  // went idle — and "cerrar sesión" has to mean it is closed.
  if (token) {
    try {
      await fetch(`${API_URL}/api/v1/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
    } catch {
      // The cookie goes either way: a browser that cannot reach the API must
      // still be able to stop being logged in.
    }
  }

  cookieStore.delete('access_token')
  redirect('/login')
}

export async function getSession() {
  const cookieStore = await cookies()
  const token = cookieStore.get('access_token')?.value

  if (!token) {
    return null
  }

  try {
    // Usar el token directamente desde la cookie, no fetch con cookies
    // porque fetch desde server actions no envía cookies automáticamente
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000) // 5 segundos timeout

    const response = await fetch(`${API_URL}/api/v1/auth/me`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      // No usar cache para obtener datos frescos
      cache: 'no-store',
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      return null
    }

    const data = (await response.json()) as Partial<CurrentSession>
    // `/auth/me` answers with the person *and* the permission map, so the menu
    // is drawn from what the backend enforces instead of from a second copy of
    // the rules living here.
    if (data && data.user && data.user.id && data.permissions) {
      return data as CurrentSession
    }
    console.error('[getSession] Unexpected response format:', data)
    return null
  } catch (error) {
    // Silenciar errores de conexión para permitir que la página se renderice
    // El usuario simplemente no estará autenticado si el backend no está disponible
    if (error instanceof Error && error.name === 'AbortError') {
      // Timeout - backend no disponible
      return null
    }
    // Otros errores de red también se ignoran silenciosamente
    return null
  }
}

/**
 * Just the person, for callers that do not care what they may reach.
 *
 * Kept so the pages that only greet somebody by name did not all have to learn
 * about permissions the day the endpoint grew them.
 */
export async function getCurrentUser(): Promise<UserRead | null> {
  const session = await getSession()
  return session ? session.user : null
}
