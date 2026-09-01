import { Badge } from '@/components/ui/badge'
import { formatMoment } from '@/lib/catalog/format'
import { caseKindLabel, sectionLabel, type Case } from '@/lib/triage/types'

/**
 * El encabezado de un caso abierto: qué es, de qué área, y hace cuánto espera.
 *
 * Vive aparte porque ahora lo usan dos paneles. El genérico —el de los pasos—
 * resuelve las clases de caso que se contestan eligiendo entre opciones; el de
 * ventas resuelve las dos que se contestan mirando dos versiones de una venta o
 * completando un dato. Son cuerpos distintos y **la misma cabeza**: quien
 * recorre la cola tiene que ver lo mismo arriba en todos los casos, o la
 * pantalla se lee como dos pantallas.
 */
export function CaseHeader({ item }: { item: Case }) {
  const pending = item.status === 'PENDING'

  return (
    <header className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="section-label">{caseKindLabel(item.kind)}</span>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>{sectionLabel(item.section)}</span>
          <span className="amount">{formatMoment(item.created_at)}</span>
          {item.occurrences > 1 && <span>se repitió {item.occurrences} veces</span>}
          {/*
            Cuánto hace que espera, y si eso ya es demasiado (RF-16, RF-17).
            El número lo calcula el backend contra el parámetro que el dueño
            mueve (RF-18), así que la pantalla no decide nada acá: lo muestra.
            Demorado es un estado del caso, así que es una píldora (`UI-03`).
          */}
          {pending && (
            <span>
              {item.waiting_days === 0
                ? 'llegó hoy'
                : `espera hace ${item.waiting_days} ${item.waiting_days === 1 ? 'día' : 'días'}`}
            </span>
          )}
          {pending && item.is_stale && <Badge tone="warn">Demorado</Badge>}
        </div>
      </div>
      <h2 className="text-lg font-semibold text-foreground">{item.reason}</h2>
    </header>
  )
}
