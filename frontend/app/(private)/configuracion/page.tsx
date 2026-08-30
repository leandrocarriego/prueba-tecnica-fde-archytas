import { NoPermission } from '@/components/common/NoPermission'
import { ParameterRow } from '@/components/operations/ParameterRow'
import { fetchFromApi } from '@/lib/api/server'
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
 * anybody else gets nothing back and lands on the refusal below — hiding a link
 * was never the restriction.
 */
export default async function ParametersPage() {
  const parameters = await fetchFromApi<Parameter[]>('/operations/parameters')

  if (parameters === null) {
    return <NoPermission what="los parámetros del sistema" />
  }

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
