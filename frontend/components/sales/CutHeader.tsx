import * as React from 'react'

import { Day } from '@/components/ui/amount'

interface CutHeaderProps {
  /** `h1` en el encabezado de la pantalla, `h2` en el de un corte. */
  as?: 'h1' | 'h2'
  title: string
  since: string | null
  until: string | null
  /** Qué se dice cuando el corte no tiene ventana elegida. */
  whole: string
  /** El control de período de **este** corte, y de ningún otro (`RF-05`). */
  children: React.ReactNode
}

/**
 * El encabezado de un corte del tablero, con la forma de la guía visual (`3b`):
 * el título a la izquierda, el período **como un hecho** debajo, y el control
 * que lo cambia a la derecha.
 *
 * Que la ventana se lea como una frase —«del 01/01/2026 al 31/08/2026»— y no
 * como dos campos de fecha es lo que hace que el número de abajo se entienda
 * sin mirar el control: un total sin período es un número sin unidad.
 *
 * El control viene por `children` porque cada corte trae el suyo: la
 * facturación y el catálogo eligen su período por separado, y mezclarlos sería
 * exactamente lo que `RF-05` prohíbe.
 */
export function CutHeader({ as = 'h2', title, since, until, whole, children }: CutHeaderProps) {
  const Heading = as
  const size = as === 'h1' ? 'text-2xl' : 'text-lg'

  return (
    <header className="flex flex-wrap items-end justify-between gap-4 rounded-xl border border-border bg-card px-6 py-5">
      <div className="space-y-1">
        <Heading className={`${size} font-semibold tracking-tight text-foreground`}>
          {title}
        </Heading>
        <p className="text-sm text-muted-foreground">
          <Window since={since} until={until} whole={whole} />
        </p>
      </div>
      {children}
    </header>
  )
}

/**
 * La ventana del corte, dicha entera.
 *
 * Los cuatro casos se escriben por separado porque el tablero los tiene los
 * cuatro: sólo «desde» es una ventana abierta hacia adelante, y decirla «del X
 * al —» es un renglón que no significa nada.
 */
function Window({
  since,
  until,
  whole,
}: {
  since: string | null
  until: string | null
  whole: string
}) {
  if (since && until) {
    return (
      <>
        Del <Day value={since} /> al <Day value={until} />.
      </>
    )
  }
  if (since) {
    return (
      <>
        Desde el <Day value={since} />.
      </>
    )
  }
  if (until) {
    return (
      <>
        Hasta el <Day value={until} />.
      </>
    )
  }
  return <>{whole}</>
}
