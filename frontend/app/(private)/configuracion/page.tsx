import { NoPermission } from '@/components/common/NoPermission'
import { AlertRoutes } from '@/components/notifications/AlertRoutes'
import { ParameterRow } from '@/components/operations/ParameterRow'
import { readFromApi } from '@/lib/api/server'
import type { AlertRoute } from '@/lib/notifications/types'
import type { Parameter } from '@/lib/operations/types'
import { ErrorState } from '@/components/ui/state'
import { Card } from '@/components/ui/card'
import { Notice } from '@/components/ui/notice'

export const metadata = {
  title: 'Parámetros del sistema — Plataforma Cordillera',
}

/**
 * The one screen where every parameter of the system lives (RF-01).
 *
 * "The one screen" is a business rule, not a layout preference: the signed spec
 * says there are no parameters hidden inside the screen of the functionality
 * that uses them. That is why `/precios/configuracion` redirects here instead
 * of still holding the two it used to.
 *
 * The list is the backend's — it is drawn from the catalog that also validates
 * the ranges, so what the screen offers and what the API accepts cannot drift
 * apart. Including the honest part: a parameter nothing reads yet is shown
 * saying so instead of pretending to be a knob.
 *
 * How many of those there are is not written down here, on purpose. It is the
 * catalog's answer and it changes every time a feature lands — this comment
 * used to carry a number, and it was wrong twice: first counting a parameter
 * that was already being read, and then counting at all. The banner below asks
 * `has_effect` on every render, which is the only count that cannot go stale.
 *
 * The gate is the endpoint. `GET /operations/parameters` is owner-only, so
 * anybody else is refused and lands on the refusal below — hiding a link was
 * never the restriction. What the refusal is *not* is the answer to everything
 * else: an unreachable backend is read here as an outage and said as one,
 * because "pedíselo al dueño" is advice nobody can act on when the API is down.
 */
export default async function ParametersPage() {
  const [read, routes] = await Promise.all([
    readFromApi<Parameter[]>('/operations/parameters'),
    // Quién recibe cada tipo de aviso (RF-37 de 007). Misma sección de
    // permisos que los parámetros, así que quien llega a una llega a la otra.
    readFromApi<AlertRoute[]>('/alerts/routes'),
  ])

  if (!read.ok) {
    if (read.failure === 'unauthorized') {
      return <NoPermission what="los parámetros del sistema" />
    }
    return (
      <div className="max-w-3xl space-y-6">
        <h1 className="text-2xl font-bold">Parámetros del sistema</h1>
        <ErrorState title="No pudimos traer los parámetros.">
          Probá de nuevo en unos minutos.
        </ErrorState>
      </div>
    )
  }

  const parameters = read.data
  const waiting = parameters.filter(parameter => !parameter.has_effect).length

  return (
    <div className="max-w-3xl space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Parámetros del sistema</h1>
        <p className="text-sm text-muted-foreground">
          Estos valores los decidís vos y rigen para todo el equipo. Cada cambio queda registrado en
          el historial.
        </p>
      </header>

      {/* El aviso va arriba de los parámetros que califica (`RF-14`). */}
      {waiting > 0 && (
        <Notice
          tone="warn"
          title={
            waiting === 1
              ? 'Hay un parámetro que todavía no tiene efecto'
              : `Hay ${waiting} parámetros que todavía no tienen efecto`
          }
        >
          Se guardan y quedan listos, pero la funcionalidad que los usa todavía no está construida.
          Cuando se construya, va a encontrar el valor que hayas elegido.
        </Notice>
      )}

      <Card>
        {parameters.map(parameter => (
          <ParameterRow key={parameter.key} parameter={parameter} />
        ))}
      </Card>

      {routes.ok && <AlertRoutes routes={routes.data} />}
    </div>
  )
}
