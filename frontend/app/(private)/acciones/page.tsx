import Link from 'next/link'
import { redirect } from 'next/navigation'

import { getSession } from '@/app/actions/auth'
import { actionsFor } from '@/lib/operations/actions'
import { Empty } from '@/components/ui/state'

export const metadata = {
  title: 'Acciones — Plataforma Cordillera',
}

/**
 * One screen with everything a person can load or correct (H3).
 *
 * Each card leads to the screen where the action is actually done, and it is
 * there that whoever ran it is told whether it was applied or why it failed
 * (RF-22) — the result belongs next to the thing that produced it, not on a
 * launcher that has already been left behind.
 *
 * The list is filtered by the permission map the backend hands out with the
 * session, so purchasing and sales see different sets (RF-21). Filtering is a
 * convenience: every route refuses on its own, and this screen never widens
 * what anybody may touch.
 */
export default async function ActionsPage() {
  const session = await getSession()
  if (!session) redirect('/login')

  const actions = actionsFor(session.permissions)

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Acciones</h1>
        <p className="text-sm text-muted-foreground">
          Todo lo que podés cargar y corregir, en un solo lugar. Cada cambio queda registrado con tu
          nombre en el{' '}
          <Link className="text-link hover:underline" href="/historial">
            historial
          </Link>
          .
        </p>
      </header>

      {actions.length === 0 ? (
        <Empty title="Tu acceso no tiene todavía ninguna acción de carga o corrección." />
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {actions.map(action => (
            <li key={action.id}>
              {/*
                Cada acción es una tarjeta que lleva a su pantalla. Ninguna va
                en naranja: es una lista de decisiones, y ninguna es más
                importante que otra (`RF-21`).
              */}
              <Link
                className="block h-full rounded-lg border border-border bg-card p-5 transition-colors hover:bg-accent"
                href={action.href}
              >
                <span className="block font-medium">{action.label}</span>
                <span className="mt-1 block text-sm text-muted-foreground">
                  {action.description}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
