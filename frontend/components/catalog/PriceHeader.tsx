import Link from 'next/link'

import { UpdateNowButton } from '@/components/catalog/UpdateNowButton'
import { formatMoment } from '@/lib/catalog/format'
import type { PriceUpdateStatus } from '@/lib/catalog/types'
import { Badge } from '@/components/ui/badge'

interface PriceHeaderProps {
  total: number
  status: PriceUpdateStatus | null
}

/**
 * El encabezado de la lista de precios (guía visual `3k`).
 *
 * La sincronización se muestra **como un hecho con hora y resultado**, no como
 * un ícono girando: el conteo de productos y cuándo fue la última corrida
 * exitosa, más una píldora que dice si está al día o atrasada. La píldora sale
 * de `is_stalled`, el mismo dato con el que el aviso rojo grita cuando la
 * extracción dejó de funcionar.
 *
 * Dos controles a la derecha: «Historial de sync» (contorno, navegación) y
 * «Actualizar ahora» (tinta). El naranja no está acá: se gasta abajo.
 */
export function PriceHeader({ total, status }: PriceHeaderProps) {
  const stalled = status?.is_stalled ?? false
  const lastSuccess = status?.last_success_at ?? null

  return (
    <header className="flex flex-wrap items-end justify-between gap-4 rounded-xl border border-border bg-card px-6 py-5">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Lista de precios</h1>
        <p className="text-sm text-muted-foreground">
          {total} {total === 1 ? 'producto' : 'productos'}
          {' · '}
          {lastSuccess === null
            ? 'todavía sin sincronizar'
            : `última actualización automática ${formatMoment(lastSuccess)}`}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Badge tone={stalled ? 'danger' : 'ok'}>{stalled ? 'Atrasado' : 'Al día'}</Badge>
        <Link
          className="inline-flex h-10 items-center rounded-md border border-input bg-card px-4 text-sm font-semibold text-foreground hover:bg-muted"
          href="/precios/historial"
        >
          Historial de sync
        </Link>
        <UpdateNowButton />
      </div>
    </header>
  )
}
