import { NoPermission } from '@/components/common/NoPermission'
import { ParameterCard } from '@/components/operations/ParameterCard'
import { readFromApi } from '@/lib/api/server'
import type { Parameter, SyncSource } from '@/lib/operations/types'
import { ErrorState } from '@/components/ui/state'
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
 * **Las frecuencias de consulta al portal no están acá, están en
 * «Actualizaciones»**, que es la pestaña de al lado. No es una excepción a
 * RF-01 sino su forma: los cuatro parámetros de cada cuánto se consulta seguían
 * estando todos juntos, pero repartidos entre dieciséis tarjetas y cada uno
 * nombrado por lo suyo, así que nada decía que los cuatro contestan la misma
 * pregunta. Siguen en Configuración, a una pestaña de distancia, y no dentro de
 * la pantalla de la funcionalidad que los usa, que es lo que RF-01 prohíbe.
 *
 * Es la primera pestaña de «Configuración» y no una pantalla suelta: el
 * encabezado y la fila de pestañas los pone `layout.tsx`, y acá queda lo que es
 * de los parámetros. La regla de RF-01 no se movió — los parámetros siguen
 * estando todos juntos en un solo lugar.
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
 * **La forma es la grilla de la guía** (`docs/design/` 3m): cada parámetro es
 * una tarjeta, y cada tarjeta se guarda sola. Un único «Guardar cambios» al pie
 * se llevaría por delante lo que RF-06 pide —que un valor rechazado diga *cuál*
 * fue— y dejaría al dueño adivinando cuál de dieciséis no entró.
 *
 * The gate is the endpoint. `GET /operations/parameters` is owner-only, so
 * anybody else is refused and lands on the refusal below — hiding a link was
 * never the restriction. What the refusal is *not* is the answer to everything
 * else: an unreachable backend is read here as an outage and said as one,
 * because "pedíselo al dueño" is advice nobody can act on when the API is down.
 */
export default async function ParametersPage() {
  const [read, sources] = await Promise.all([
    readFromApi<Parameter[]>('/operations/parameters'),
    // Para saber **cuáles** son las frecuencias de consulta al portal, que se
    // muestran en «Actualizaciones» al lado de la fuente que gobiernan. Se
    // preguntan en vez de escribirse acá: una lista de claves copiada sería una
    // lista para acordarse de corregir el día que aparezca otra fuente, y el
    // costo de olvidarse es un parámetro que aparece dos veces o ninguna.
    readFromApi<SyncSource[]>('/operations/syncs'),
  ])

  if (!read.ok) {
    if (read.failure === 'unauthorized') {
      return <NoPermission what="los parámetros del sistema" />
    }
    return (
      <ErrorState title="No pudimos traer los parámetros.">
        Probá de nuevo en unos minutos.
      </ErrorState>
    )
  }

  const elsewhere = new Set(sources.ok ? sources.data.map(source => source.interval_key) : [])
  const parameters = read.data.filter(parameter => !elsewhere.has(parameter.key))
  const waiting = parameters.filter(parameter => !parameter.has_effect).length

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold">Parámetros del sistema</h2>
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

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {parameters.map(parameter => (
          <ParameterCard key={parameter.key} parameter={parameter} />
        ))}
      </div>
    </div>
  )
}
