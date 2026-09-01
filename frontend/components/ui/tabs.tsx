'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { isCurrentPath } from '@/lib/ui/current'
import { cn } from '@/lib/utils'

/**
 * Las pestañas de una pantalla que tiene secciones.
 *
 * **Enlaces, no estado.** Cada sección es una ruta propia, así que se puede
 * compartir, marcar y recargar sin perder dónde estaba parada la persona, y
 * cada una trae sus datos en el servidor en vez de pedirlos todos por si acaso.
 * Lo único que necesita el navegador es saber cuál está abierta, y eso lo dice
 * la ruta.
 *
 * La forma es la de la guía (`docs/design/`, `.tabs`): una fila de rótulos
 * sobre una línea, con la abierta subrayada en tinta. Sin color de acento — el
 * naranja está reservado para lo urgente y para la acción principal (`UI-05`), y
 * cambiar de sección no es ninguna de las dos.
 */
export interface Tab {
  href: string
  label: string
}

export function Tabs({ tabs, label }: { tabs: ReadonlyArray<Tab>; label: string }) {
  const pathname = usePathname()
  const hrefs = tabs.map(tab => tab.href)

  return (
    <nav aria-label={label} className="flex gap-1 overflow-x-auto border-b border-border">
      {tabs.map(tab => {
        const current = isCurrentPath(pathname, tab.href, hrefs)
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={current ? 'page' : undefined}
            className={cn(
              '-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm transition-colors',
              current
                ? 'border-foreground font-semibold text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {tab.label}
          </Link>
        )
      })}
    </nav>
  )
}
