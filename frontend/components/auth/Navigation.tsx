'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { logoutAction } from '@/app/actions/auth'
import { canSee, type Permissions, type Section } from '@/lib/auth/permissions'
import type { components } from '@/lib/api/types'
import { isCurrentPath } from '@/lib/ui/current'
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
 *
 * **En una pantalla angosta la barra se pliega** (RF-41 de la 006). Apilada
 * entera medía 832px sobre un teléfono de 664px: la primera pantalla era el
 * menú y había que desplazarse una pantalla y media para ver la sección que se
 * vino a consultar. Plegada deja una franja con dónde está parada la persona y
 * el botón que abre el resto. Desde `md` no cambia nada: la barra sigue fija a
 * la izquierda, y ahí no hay nada que plegar.
 */
interface Entry {
  href: string
  label: string
  /** Sin sección: cualquier sesión la alcanza. */
  section?: Section
  /**
   * De qué cuenta lleva la señal roja, si lleva alguna.
   *
   * El número no vive acá: lo trae el layout con la sesión, porque es un dato
   * del backend y cambia en cada carga. Lo que la entrada declara es **cuál**
   * de esas cuentas le corresponde, que sí es una propiedad suya.
   */
  counter?: keyof Counters
}

/**
 * Los números que el menú puede mostrar sobre una entrada.
 *
 * Hoy es uno solo —lo que espera una decisión—, y está tipado como registro
 * para que agregar el siguiente (la guía visual también dibuja «Avisos 7») sea
 * una línea acá y otra en el layout, y no otra prop suelta.
 */
export interface Counters {
  triage: number
}

interface Group {
  title: string | null
  entries: ReadonlyArray<Entry>
}

const GROUPS: ReadonlyArray<Group> = [
  {
    title: null,
    entries: [
      { href: '/tablero', label: 'Tablero', section: 'DASHBOARD' },
      /*
       * «Para decidir» va acá arriba, pegada al tablero, y no dentro de un
       * grupo: **no es de un área**. Es la única cola de la plataforma —caen
       * ahí los precios, las facturas, el padrón, el buzón y las ventas— y
       * meterla bajo «Catálogo y datos», que es donde estaba, la hacía parecer
       * una pantalla del catálogo. Con el tablero forman el par con el que se
       * abre el día: qué pasó, y qué hay que decidir.
       *
       * No nombra sección. Pedía `PRICES`, que era cierto cuando en la cola
       * sólo había precios y dejó de serlo cuando las ventas empezaron a caer
       * ahí: le cerraba la puerta a Julián, el dueño de esa mitad. La pantalla
       * recorta lo que *muestra* a las áreas que el que mira alcanza, en vez de
       * cerrarse.
       */
      { href: '/revision', label: 'Para decidir', counter: 'triage' },
    ],
  },
  {
    title: 'Compras',
    entries: [
      { href: '/proveedores', label: 'Proveedores', section: 'SUPPLIERS' },
      { href: '/facturas', label: 'Facturas', section: 'PURCHASE_INVOICES' },
      { href: '/ordenes', label: 'Órdenes de compra', section: 'PURCHASE_ORDERS' },
      { href: '/calendario', label: 'Calendario', section: 'CALENDAR' },
    ],
  },
  {
    title: 'Catálogo y datos',
    entries: [
      /*
       * Ventas encabeza el grupo en vez de ser un grupo propio: hay una sola
       * pantalla de ventas, y un título con una sola entrada debajo es un
       * renglón que no agrupa nada. `RF-22` se sigue cumpliendo —la sección
       * aparece en el menú y se abre desde ahí—; en qué grupo vive no lo fija
       * la spec, y lo decidió el dueño.
       *
       * `/ventas` es el listado de ventas, y desde que lo es no hay una segunda
       * pantalla en el área: lo repetido y lo roto se decide en «Para decidir»,
       * con todo lo demás que la plataforma aparta. El `href` marca la entrada
       * desde cualquier ruta que empiece con `/ventas`.
       */
      { href: '/ventas', label: 'Ventas', section: 'SALES' },
      { href: '/precios', label: 'Catálogo y precios', section: 'PRICES' },
      { href: '/rubros', label: 'Rubros', section: 'PRODUCT_CATEGORIES' },
    ],
  },
  {
    title: 'Sistema',
    entries: [
      /*
       * El historial no nombra sección, igual que `/health`: cualquier sesión
       * lo alcanza. Recorta lo que *muestra* a las secciones que el que mira
       * alcanza (RF-19) en vez de cerrar la puerta. Se llama «Actividad» en el
       * menú —es lo que la persona viene a buscar—, y la ruta sigue siendo
       * `/historial`, que es lo que la pantalla es por dentro.
       */
      { href: '/historial', label: 'Actividad' },
      /*
       * Una entrada para tres pantallas: los parámetros, los accesos y a quién
       * le llega cada aviso viven adentro de `/configuracion`, en pestañas.
       *
       * Nombra `SYSTEM_PARAMETERS` y no las dos secciones que hay ahí adentro
       * porque las dos son del dueño y de nadie más: quien alcanza una alcanza
       * la otra, así que una entrada condicionada a la segunda mostraría
       * exactamente las mismas veces. El día que eso deje de ser cierto, la que
       * decide qué pestañas se ven es la pantalla —`configuracion/layout.tsx`
       * las filtra por sección— y acá habría que quitar la sección, como en
       * «Para decidir».
       */
      { href: '/configuracion', label: 'Configuración', section: 'SYSTEM_PARAMETERS' },
      { href: '/health', label: 'Salud' },
    ],
  },
]

export function Navigation({
  user,
  permissions,
  counters,
}: {
  user: UserRead
  permissions: Permissions
  /** Las cuentas que el menú muestra. Sin ellas no dibuja ninguna señal. */
  counters?: Partial<Counters>
}) {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  const groups = GROUPS.map(group => ({
    ...group,
    entries: group.entries.filter(entry => !entry.section || canSee(permissions, entry.section)),
  })).filter(group => group.entries.length > 0)

  const hrefs = groups.flatMap(group => group.entries.map(entry => entry.href))
  const fullName = `${user.name}${user.last_name ? ` ${user.last_name}` : ''}`
  // Dónde está parada la persona, para decirlo en la franja plegada: con el
  // menú cerrado, el nombre de la sección es lo único que lo dice.
  const aqui = groups
    .flatMap(group => group.entries)
    .find(entry => isCurrentPath(pathname, entry.href, hrefs))

  return (
    <aside className="flex w-full flex-none flex-col bg-primary text-primary-foreground md:sticky md:top-0 md:h-dvh md:w-60">
      <div className="flex items-center justify-between gap-3 px-5 py-5">
        <Link href="/" className="flex items-center gap-3">
          <span className="flex size-9 flex-none items-center justify-center rounded-lg border-2 border-brand text-sm font-bold">
            FC
          </span>
          <span className="leading-tight">
            <span className="block text-sm font-semibold">Cordillera</span>
            <span className="block text-[11px] text-white/45">
              {/* Plegada, la franja dice la sección; desplegada y en escritorio, el producto. */}
              <span className="md:hidden">{aqui?.label ?? 'Gestión interna'}</span>
              <span className="hidden md:inline">Gestión interna</span>
            </span>
          </span>
        </Link>
        <button
          type="button"
          onClick={() => setOpen(current => !current)}
          aria-expanded={open}
          aria-controls="menu-principal"
          className="cursor-pointer rounded-md border border-white/15 px-3 py-1.5 text-[13px] text-white/75 hover:bg-white/5 hover:text-white md:hidden"
        >
          {open ? 'Cerrar' : 'Menú'}
        </button>
      </div>

      {/*
        Plegado en un teléfono, siempre abierto desde `md`: la barra de
        escritorio no tiene botón, así que no puede quedar cerrada sin salida.
      */}
      <div
        id="menu-principal"
        className={cn('min-h-0 flex-1 flex-col md:flex', open ? 'flex' : 'hidden')}
      >
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
                  /*
                   * Elegir algo cierra el menú: en un teléfono, quedarse
                   * abierto tapa exactamente la pantalla que la persona acaba
                   * de pedir. Va sobre cada enlace y no sobre el contenedor
                   * —que es un `div`, y un `div` con `onClick` no se alcanza
                   * con el teclado— ni en un efecto que mire la ruta: cerrar es
                   * la consecuencia del clic, no de haber navegado.
                   */
                  onClick={() => setOpen(false)}
                  aria-current={isCurrentPath(pathname, entry.href, hrefs) ? 'page' : undefined}
                  className={cn(
                    'block rounded-md px-2.5 py-1.5 text-[13.5px] transition-colors',
                    isCurrentPath(pathname, entry.href, hrefs)
                      ? 'bg-white/10 font-semibold text-white'
                      : 'text-white/65 hover:bg-white/5 hover:text-white'
                  )}
                >
                  <span className="flex items-center justify-between gap-2">
                    {entry.label}
                    {/*
                      Cuántos esperan una decisión, en rojo y sobre la entrada.
                      **Cero no se dibuja**: un contador en cero es una alarma
                      apagada que igual ocupa lugar, y a la semana nadie mira
                      ninguno de los dos estados. La cuenta ya viene recortada a
                      las áreas que esta persona alcanza (RF-12), así que el
                      número del menú y el de la pantalla son el mismo.
                    */}
                    {entry.counter && (counters?.[entry.counter] ?? 0) > 0 && (
                      <span className="amount inline-flex min-w-5 flex-none items-center justify-center rounded-full bg-destructive px-1.5 py-0.5 text-[10px] font-semibold text-destructive-foreground">
                        {counters?.[entry.counter]}
                      </span>
                    )}
                  </span>
                </Link>
              ))}
            </div>
          ))}
        </nav>

        {/* RF-03: mientras alguien trabaja, la pantalla dice quién. */}
        <div className="border-t border-white/10 px-3 py-3">
          <Link
            href="/mi-cuenta"
            onClick={() => setOpen(false)}
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
