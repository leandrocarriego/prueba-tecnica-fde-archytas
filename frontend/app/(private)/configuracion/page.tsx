import { NoPermission } from '@/components/common/NoPermission'
import { ParameterRow } from '@/components/operations/ParameterRow'
import { readFromApi } from '@/lib/api/server'
import type { Parameter } from '@/lib/operations/types'

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
 * apart. Including the honest part: five of the seven are not read by anything
 * yet, and each of those says so out loud rather than pretending to be a knob.
 *
 * The gate is the endpoint. `GET /operations/parameters` is owner-only, so
 * anybody else is refused and lands on the refusal below — hiding a link was
 * never the restriction. What the refusal is *not* is the answer to everything
 * else: an unreachable backend is read here as an outage and said as one,
 * because "pedíselo al dueño" is advice nobody can act on when the API is down.
 */
export default async function ParametersPage() {
  const read = await readFromApi<Parameter[]>('/operations/parameters')

  if (!read.ok) {
    if (read.failure === 'unauthorized') {
      return <NoPermission what="los parámetros del sistema" />
    }
    return (
      <main className="mx-auto max-w-3xl space-y-6 p-8">
        <h1 className="text-2xl font-bold">Parámetros del sistema</h1>
        <p className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-900">
          No pudimos traer los parámetros. Probá de nuevo en unos minutos.
        </p>
      </main>
    )
  }

  const parameters = read.data
  const waiting = parameters.filter(parameter => !parameter.has_effect).length

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Parámetros del sistema</h1>
        <p className="text-sm text-muted-foreground">
          Estos valores los decidís vos y rigen para todo el equipo. Cada cambio queda registrado en
          el historial.
        </p>
      </header>

      {waiting > 0 && (
        <p className="rounded border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          {waiting === 1
            ? 'Hay un parámetro que todavía no tiene efecto: '
            : `Hay ${waiting} parámetros que todavía no tienen efecto: `}
          se guardan y quedan listos, pero la funcionalidad que los usa todavía no está construida.
          Cuando se construya, va a encontrar el valor que hayas elegido.
        </p>
      )}

      <section className="rounded border">
        {parameters.map(parameter => (
          <ParameterRow key={parameter.key} parameter={parameter} />
        ))}
      </section>
    </main>
  )
}
