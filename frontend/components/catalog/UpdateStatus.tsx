import Link from 'next/link'

import { formatMoment } from '@/lib/catalog/format'
import type { PriceUpdateStatus } from '@/lib/catalog/types'
import { Notice } from '@/components/ui/notice'
import { Empty } from '@/components/ui/state'

interface UpdateStatusProps {
  status: PriceUpdateStatus | null
}

/**
 * When the last successful update was, and whether it stopped working.
 *
 * RF-09, RF-11 and the tally of RF-27. The warning is on the screen and not
 * only on WhatsApp on purpose: Evolution API is a free third-party service, and
 * an alert that depends on it is an alert that can silently not exist.
 *
 * The tally lives here rather than in the button because an update also ends
 * when nobody asked for it: the scheduled one is the common case, and it has no
 * button to report back to.
 */
export function UpdateStatus({ status }: UpdateStatusProps) {
  if (status === null) {
    return <Empty title="No pudimos consultar el estado de la actualización." />
  }

  if (status.is_stalled) {
    // El aviso va **arriba** de los precios que califica, con todo lo que hace
    // falta para entenderlo (`RF-14`).
    return (
      <Notice tone="danger" title="La actualización de precios dejó de funcionar.">
        Van {status.consecutive_failures} consultas seguidas sin éxito. Última actualización
        exitosa: {formatMoment(status.last_success_at)}. Los precios de abajo pueden estar
        desactualizados.
      </Notice>
    )
  }

  return (
    <div className="space-y-1">
      <p className="text-sm text-muted-foreground">
        Última actualización exitosa: {formatMoment(status.last_success_at)} · Se consulta el portal
        cada {status.interval_hours} h · Se destacan las subas mayores al{' '}
        {status.highlight_threshold_pct}%
      </p>
      <SetAside rows={status.last_quarantined} />
    </div>
  )
}

/** How many rows the last update could not interpret, and where to go see them. */
function SetAside({ rows }: { rows: number | null }) {
  // Null is "no update to report on yet", which is not the same as an update
  // that set aside nothing: only the second one is worth a line on the screen.
  if (rows === null) return null

  if (rows === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No quedó ninguna fila apartada en esa actualización.
      </p>
    )
  }

  return (
    <p className="text-sm">
      <Link className="text-link hover:underline" href="/revision">
        {rows === 1
          ? '1 fila quedó apartada en esa actualización'
          : `${rows} filas quedaron apartadas en esa actualización`}
      </Link>
    </p>
  )
}
