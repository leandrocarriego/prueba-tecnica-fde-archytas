import Link from 'next/link'

import { getCurrentUser } from '@/app/actions/auth'

/**
 * Dashboard — landing page of the protected area.
 */
export default async function DashboardPage() {
  const user = await getCurrentUser()

  // Defensive check: the layout already guards this route, but avoid rendering
  // errors if there is a timing issue with the session cookie.
  if (!user) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center p-24">
        <div className="z-10 w-full max-w-5xl items-center justify-between text-sm">
          <h1 className="mb-8 text-center text-4xl font-bold">Plataforma Cordillera</h1>
          <div className="text-center">
            <p className="mb-4 text-lg">Cargando...</p>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 w-full max-w-5xl items-center justify-between text-sm">
        <h1 className="mb-8 text-center text-4xl font-bold">Plataforma Cordillera</h1>
        <div className="text-center">
          <p className="mb-4 text-lg">Bienvenido, {user.email}</p>
          <p className="text-muted-foreground">Esta es la página principal de la plataforma.</p>
          <nav className="mt-8 flex justify-center gap-6">
            <Link className="underline underline-offset-4" href="/precios">
              Lista de precios
            </Link>
            <Link className="underline underline-offset-4" href="/revision">
              Revisión
            </Link>
          </nav>
        </div>
      </div>
    </main>
  )
}
