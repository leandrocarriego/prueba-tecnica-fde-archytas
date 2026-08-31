import Link from 'next/link'

import { logoutAction } from '@/app/actions/auth'
import { canSee, type Permissions, type Section } from '@/lib/auth/permissions'
import type { components } from '@/lib/api/types'

type UserRead = components['schemas']['UserRead']

/**
 * The menu, drawn from what the backend says this person may reach.
 *
 * Every entry names its section, and the section is the same one the route
 * demands on the server. That is why there is no list of roles here: hiding a
 * link is a convenience, the refusal is the backend's, and keeping both in one
 * place is what stops them from drifting apart.
 */
const ENTRIES: ReadonlyArray<{ href: string; label: string; section: Section }> = [
  { href: '/precios', label: 'Precios', section: 'PRICES' },
  { href: '/revision', label: 'Revisión', section: 'PRICES' },
  { href: '/rubros', label: 'Rubros', section: 'PRODUCT_CATEGORIES' },
  { href: '/facturas', label: 'Facturas', section: 'PURCHASE_INVOICES' },
  { href: '/proveedores', label: 'Proveedores', section: 'SUPPLIERS' },
  { href: '/calendario', label: 'Calendario', section: 'CALENDAR' },
  { href: '/ordenes', label: 'Órdenes', section: 'PURCHASE_ORDERS' },
  { href: '/mensajes', label: 'Mensajes', section: 'SUPPLIER_MESSAGES' },
  { href: '/tablero', label: 'Tablero', section: 'DASHBOARD' },
  { href: '/accesos', label: 'Accesos', section: 'ACCESS_ADMIN' },
  { href: '/accesos/actividad', label: 'Actividad', section: 'ACCESS_LOG' },
  { href: '/configuracion', label: 'Parámetros', section: 'SYSTEM_PARAMETERS' },
]

export function Navigation({ user, permissions }: { user: UserRead; permissions: Permissions }) {
  const visible = ENTRIES.filter(entry => canSee(permissions, entry.section))

  return (
    <header className="border-b bg-white">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-6 py-3">
        <Link href="/" className="font-semibold">
          Cordillera
        </Link>

        <nav className="flex flex-1 flex-wrap gap-4 text-sm">
          {visible.map(entry => (
            <Link key={entry.href} href={entry.href} className="hover:underline">
              {entry.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3 text-sm">
          {/*
            Two more that name no section, for the same reason `/health` does
            not: any session reaches them. The history narrows what it *shows*
            to the sections the caller reaches (RF-19) rather than closing the
            door, and the actions screen lists whatever that person may run,
            which for somebody with nothing is an honest empty state.
          */}
          <Link href="/acciones" className="text-muted-foreground hover:underline">
            Acciones
          </Link>
          <Link href="/historial" className="text-muted-foreground hover:underline">
            Historial
          </Link>
          {/*
            Not in ENTRIES, and not an oversight: every entry there names the
            section its route demands, and this one demands none — any session
            may read it. Giving it a section to fit the list would hide it from
            whoever lacks that section, which is the opposite of true.
          */}
          <Link href="/health" className="text-muted-foreground hover:underline">
            Salud
          </Link>
          {/* RF-03: while somebody is working, the screen says who. */}
          <Link href="/mi-cuenta" className="text-muted-foreground hover:underline">
            {user.name}
            {user.last_name ? ` ${user.last_name}` : ''}
          </Link>
          <form action={logoutAction}>
            <button
              type="submit"
              className="cursor-pointer rounded border px-3 py-1 hover:bg-gray-50"
            >
              Cerrar sesión
            </button>
          </form>
        </div>
      </div>
    </header>
  )
}
