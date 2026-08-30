import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Rutas públicas que NO requieren autenticación.
  //
  // Todas las páginas de (auth) van acá, y no es una lista de conveniencia: son
  // exactamente las que visita alguien que **no puede** iniciar sesión. Una
  // invitación o un enlace de recuperación detrás del guard redirige a un login
  // que esa persona todavía no puede pasar, que es el único momento en que
  // necesitaba el enlace.
  const publicPaths = [
    '/login',
    '/reset-password',
    '/invitacion',
    '/recuperar',
    '/api', // API routes pueden tener su propia autenticación
  ]
  const isPublicPath = publicPaths.some(path => pathname.startsWith(path))

  // Si es una ruta pública, permitir acceso sin verificar cookie
  if (isPublicPath) {
    return NextResponse.next()
  }

  // Todas las demás rutas requieren autenticación
  // Esto protege automáticamente cualquier ruta que no esté en publicPaths
  // Incluyendo rutas dentro de (private)/*, etc.
  const token = request.cookies.get('access_token')

  // Si no hay token, redirigir a login
  // NOTA: Después de un login, puede haber un pequeño delay antes de que la cookie esté disponible
  // El layout de (private) también verifica la autenticación, así que si la cookie no está aquí,
  // el layout redirigirá a /login
  if (!token) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }

  // Si hay token, permitir acceso
  // La validación del token se hace en los layouts/components cuando se necesitan datos
  return NextResponse.next()
}

export const config = {
  // Proteger todas las rutas excepto las públicas
  // El matcher usa una expresión negativa para excluir rutas públicas
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - login (página de login)
     * - reset-password (pedir un enlace de recuperación)
     * - invitacion (definir la clave de un acceso nuevo)
     * - recuperar (definir una clave nueva)
     * - estado (página pública de estado del servicio)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|login|reset-password|invitacion|recuperar|estado).*)',
  ],
}
