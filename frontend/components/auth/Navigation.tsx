'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { logoutAction } from '@/app/actions/auth'
import { canSee, type Permissions, type Section } from '@/lib/auth/permissions'
import type { components } from '@/lib/api/types'
import { cn } from '@/lib/utils'

type UserRead = components['schemas']['UserRead']

/**
 * El menú, dibujado a partir de lo que el backend dice que esta persona alcanza.
 *
 * Cada entrada nombra su sección, y la sección es la misma que la ruta exige en
 * el servidor. Por eso acá no hay ninguna lista de roles: esconder un enlace es
 * una comodidad, la negativa es del backend, y tener las dos cosas en un solo
 * lugar es lo que impide que se separen.
 *
 * La forma es la de la guía visual (`docs/design/`): barra lateral fija en
 * tinta grafito, agrupada por área del negocio. Lo que no se puede ver no
 * aparece —ni el grupo, si le quedó todo afuera—, en vez de mostrar un botón
 * que devuelve error.
 */
interface Entry {
  href: string
  label: string
  /** Sin sección: cualquier sesión la alcanza. */
  section?: Section
}

interface Group {
  title: string | null
  entries: ReadonlyArray<Entry>
}

const GROUPS: ReadonlyArray<Group> = [
  {
    title: null,
    entries: [{ href: '/tablero', label: 'Tablero', section: 'DASHBOARD' }],
  },
  {
    title: 'Compras',
    entries: [
      { href: '/proveedores', label: 'Proveedores', section: 'SUPPLIERS' },
      { href: '/facturas', label: 'Facturas', section: 'PURCHASE_INVOICES' },
      { href: '/ordenes', label: 'Órdenes de compra', section: 'PURCHASE_ORDERS' },
      { href: '/calendario', label: 'Calendario', section: 'CALENDAR' },
      { href: '/mensajes', label: 'Mensajes', section: 'SUPPLIER_MESSAGES' },
    ],
  },
  {
    title: 'Catálogo y datos',
    entries: [
      { href: '/precios', label: 'Catálogo y precios', section: 'PRICES' },
      { href: '/rubros', label: 'Rubros', section: 'PRODUCT_CATEGORIES' },
      { href: '/revision', label: 'Revisar esto', section: 'PRICES' },
    ],
  },
  {
    title: 'Sistema',
    entries: [
      /*
       * Estas tres no nombran sección, igual que `/health`: cualquier sesión
       * las alcanza. El historial recorta lo que *muestra* a las secciones que
       * el que mira alcanza (RF-19) en vez de cerrar la puerta, y la pantalla
       * de acciones lista las que esa persona puede correr, que para alguien
       * sin ninguna es un vacío honesto.
       */
      { href: '/acciones', label: 'Acciones' },
      { href: '/historial', label: 'Historial' },
      { href: '/accesos', label: 'Accesos', section: 'ACCESS_ADMIN' },
      { href: '/accesos/actividad', label: 'Actividad', section: 'ACCESS_LOG' },
      { href: '/configuracion', label: 'Parámetros', section: 'SYSTEM_PARAMETERS' },
      { href: '/health', label: 'Salud' },
    ],
  },
]

/** La entrada más específica que coincide con la ruta actual queda marcada. */
function isCurrent(pathname: string, href: string, all: ReadonlyArray<string>): boolean {
  if (pathname !== href && !pathname.startsWith(`${href}/`)) return false
  return !all.some(
    other => other !== href && other.length > href.length && isPrefix(pathname, other)
  )
}

function isPrefix(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`)
}

export function Navigation({ user, permissions }: { user: UserRead; permissions: Permissions }) {
  const pathname = usePathname()

  const groups = GROUPS.map(group => ({
    ...group,
    entries: group.entries.filter(entry => !entry.section || canSee(permissions, entry.section)),
  })).filter(group => group.entries.length > 0)

  const hrefs = groups.flatMap(group => group.entries.map(entry => entry.href))
  const fullName = `${user.name}${user.last_name ? ` ${user.last_name}` : ''}`

  return (
    <aside className="flex w-60 flex-none flex-col bg-primary text-primary-foreground md:sticky md:top-0 md:h-dvh">
      <Link href="/" className="flex items-center gap-3 px-5 py-5">
        <span className="flex size-9 flex-none items-center justify-center rounded-lg border-2 border-brand text-sm font-bold">
          FC
        </span>
        <span className="leading-tight">
          <span className="block text-sm font-semibold">Cordillera</span>
          <span className="block text-[11px] text-white/45">Gestión interna</span>
        </span>
      </Link>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 pb-5">
        {groups.map((group, index) => (
          <div key={group.title ?? `group-${index}`} className="space-y-0.5">
            {group.title ? (
              <p className="section-label px-2 pb-1.5 pt-1 text-white/35">{group.title}</p>
            ) : null}
            {group.entries.map(entry => (
              <Link
                key={entry.href}
                href={entry.href}
                aria-current={isCurrent(pathname, entry.href, hrefs) ? 'page' : undefined}
                className={cn(
                  'block rounded-md px-2.5 py-1.5 text-[13.5px] transition-colors',
                  isCurrent(pathname, entry.href, hrefs)
                    ? 'bg-white/10 font-semibold text-white'
                    : 'text-white/65 hover:bg-white/5 hover:text-white'
                )}
              >
                {entry.label}
              </Link>
            ))}
          </div>
        ))}
      </nav>

      {/* RF-03: mientras alguien trabaja, la pantalla dice quién. */}
      <div className="border-t border-white/10 px-3 py-3">
        <Link
          href="/mi-cuenta"
          className="flex items-center gap-2.5 rounded-md px-2 py-1.5 hover:bg-white/5"
        >
          <span className="flex size-8 flex-none items-center justify-center rounded-full bg-white/10 text-[11px] font-semibold">
            {initials(fullName)}
          </span>
          <span className="min-w-0 flex-1 truncate text-[13px] font-medium">{fullName}</span>
        </Link>
        <form action={logoutAction}>
          <button
            type="submit"
            className="mt-1 w-full cursor-pointer rounded-md px-2 py-1.5 text-left text-[13px] text-white/50 hover:bg-white/5 hover:text-white"
          >
            Cerrar sesión
          </button>
        </form>
      </div>
    </aside>
  )
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0]?.toUpperCase() ?? '')
    .join('')
}
