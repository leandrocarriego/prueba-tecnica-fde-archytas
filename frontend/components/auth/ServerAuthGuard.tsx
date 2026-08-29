import { redirect } from 'next/navigation'
import { getCurrentUser } from '@/app/actions/auth'

interface ServerAuthGuardProps {
  children: React.ReactNode
}

/**
 * Server Component que protege rutas verificando autenticación en el servidor.
 * Más seguro que el AuthGuard del cliente porque la verificación ocurre en el servidor.
 *
 * Verifica que el token sea válido haciendo una llamada al backend.
 * Si el token es inválido o no existe, redirige a /login.
 * La página de login manejará la limpieza de cookies inválidas si es necesario.
 */
export async function ServerAuthGuard({ children }: ServerAuthGuardProps) {
  const user = await getCurrentUser()

  // Si no hay usuario (token inválido o no existe), redirigir a login
  // No agregar mensaje de error aquí porque puede ser un problema de timing de cookies
  if (!user) {
    redirect('/login')
  }

  return <>{children}</>
}
