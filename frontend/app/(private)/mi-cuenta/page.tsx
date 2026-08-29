import { redirect } from 'next/navigation'

import { changeOwnPassword } from '@/app/actions/access'
import { getSession } from '@/app/actions/auth'
import { PasswordForm } from '@/components/auth/PasswordForm'

const ROLES: Record<string, string> = {
  OWNER: 'Dueño',
  PURCHASING: 'Compras',
  SALES: 'Ventas',
}

/** Your own account: who you are, and the one credential you control (RF-25). */
export default async function MiCuentaPage() {
  const session = await getSession()
  if (!session) {
    redirect('/login')
  }

  return (
    <main className="mx-auto max-w-lg space-y-8 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold">Mi cuenta</h1>
        <p className="text-muted-foreground">
          {session.user.name}
          {session.user.last_name ? ` ${session.user.last_name}` : ''} ·{' '}
          {ROLES[session.user.role] ?? session.user.role}
        </p>
      </div>

      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
        <dt className="text-muted-foreground">Entrás con</dt>
        <dd>{session.user.email}</dd>
        <dt className="text-muted-foreground">Te escribimos a</dt>
        <dd>{session.user.phone}</dd>
      </dl>

      <section className="space-y-3 rounded border p-4">
        <h2 className="font-medium">Cambiar mi clave</h2>
        <p className="text-xs text-muted-foreground">
          Al cambiarla se cierran las sesiones que tengas abiertas en otros navegadores.
        </p>
        <PasswordForm action={changeOwnPassword} etiqueta="Cambiar la clave" pideClaveActual />
      </section>
    </main>
  )
}
