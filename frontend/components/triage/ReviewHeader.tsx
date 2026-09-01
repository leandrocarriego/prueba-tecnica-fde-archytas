import Link from 'next/link'

import { formatMoment } from '@/lib/catalog/format'
import { sectionLabel } from '@/lib/triage/types'

interface ReviewHeaderProps {
  pendingTotal: number
  /** Cuántas se resolvieron hoy, en el día del negocio y no en el de UTC. */
  resolvedToday: number
  /** Cuándo llegó el más viejo que sigue esperando, o `null` si no queda ninguno. */
  oldestAt: string | null
  /** Las áreas que quien mira alcanza, tal como las manda el backend. */
  sections: string[]
  /** El área elegida, si hay una. */
  area: string | undefined
}

/**
 * El encabezado de la pantalla (guía visual `3d`).
 *
 * Dice de una las cuatro cosas que hacen falta antes de mirar la lista: cuántos
 * quedan sin resolver, **cuántos se resolvieron hoy**, hace cuánto espera el más
 * viejo —que es lo que deja ver si la cola se está abandonando antes de que sea
 * un problema (RF-16)— y que lo pendiente **no entra en ningún total**, que es
 * el motivo por el que vaciarla importa.
 *
 * Lo resuelto hoy no es decoración: una pantalla que sólo cuenta lo que falta se
 * lee como una lista que no avanza nunca, y el trabajo que sí avanzó es la razón
 * por la que hoy es más corta. El número lo cuenta el backend sobre el reloj de
 * Buenos Aires, porque entre las 21:00 y la medianoche UTC ya cambió de día.
 *
 * A la derecha, el filtro por área como control segmentado (RF-22 de la 011).
 * Las opciones las manda el backend con la página: qué áreas alcanza un rol lo
 * contesta `identity` y nadie más, y una copia de esa matriz acá sería la misma
 * regla en dos lugares. Con una sola área no se dibuja, porque no hay nada que
 * elegir — que es el caso de Marcela y el de Julián, y deja el filtro donde
 * sirve: en la pantalla del dueño, que es quien ve todo.
 *
 * Son enlaces y no botones porque filtrar es navegar: el área viaja en la
 * dirección, así que la pantalla se puede compartir y el navegador vuelve
 * atrás.
 */
export function ReviewHeader({
  pendingTotal,
  resolvedToday,
  oldestAt,
  sections,
  area,
}: ReviewHeaderProps) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4 rounded-xl border border-border bg-card px-6 py-5">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Para decidir</h1>
        <p className="text-sm text-muted-foreground">
          {pendingTotal === 0 ? 'No quedó nada sin resolver' : `${pendingTotal} sin resolver`}
          {resolvedToday > 0 &&
            ` · ${resolvedToday} ${resolvedToday === 1 ? 'resuelta hoy' : 'resueltas hoy'}`}
          {oldestAt !== null && ` · el más viejo espera desde ${formatMoment(oldestAt)}`}
          {pendingTotal > 0 && ' · lo pendiente queda fuera de todos los totales'}
        </p>
      </div>

      {sections.length > 1 && (
        <nav
          aria-label="Filtrar por área"
          className="flex flex-wrap gap-1 rounded-lg border border-border bg-background p-1"
        >
          <Chip href="/revision" label="Todas" active={!area} />
          {sections.map(section => (
            <Chip
              key={section}
              href={`/revision?area=${section}`}
              label={sectionLabel(section)}
              active={area === section}
            />
          ))}
        </nav>
      )}
    </header>
  )
}

function Chip({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link
      href={href}
      aria-current={active ? 'page' : undefined}
      className={`rounded-md px-3 py-1.5 text-xs font-semibold ${
        active
          ? 'bg-primary text-primary-foreground'
          : 'text-muted-foreground hover:text-foreground'
      }`}
    >
      {label}
    </Link>
  )
}
