'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { requestSync } from '@/app/actions/operations'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Notice } from '@/components/ui/notice'
import { formatMoment } from '@/lib/catalog/format'
import { getJobStatusLabel } from '@/lib/operations/taskStateUtils'
import type { SyncSource } from '@/lib/operations/types'
import { jobTone } from '@/lib/ui/tone'

/** Cómo se lee la unidad de un intervalo, en singular y en plural. */
const UNIDADES: Record<string, [string, string]> = {
  hours: ['hora', 'horas'],
  minutes: ['minuto', 'minutos'],
}

/** «cada 12 horas», «cada 15 minutos», «cada hora». */
function cadaCuanto(source: SyncSource): string {
  const [singular, plural] = UNIDADES[source.unit] ?? [source.unit, source.unit]
  return source.interval === 1 ? `cada ${singular}` : `cada ${source.interval} ${plural}`
}

/**
 * Las seis fuentes de las que se nutre la plataforma, miradas juntas.
 *
 * **Todo lo que el sistema sabe lo trajo del portal**, y hasta acá cada
 * extracción se administraba por su cuenta: cuatro parámetros de frecuencia
 * repartidos entre dieciséis tarjetas —cada uno nombrado por lo suyo, así que
 * nada decía que los cuatro contestan la misma pregunta— y un solo botón de
 * «traerlo ahora», el de la lista de precios, porque fue la primera que se
 * construyó.
 *
 * **No es una sola frecuencia para todo, y eso es a propósito.** Los mensajes se
 * traen cada quince minutos porque del otro lado hay alguien esperando una
 * respuesta; las ventas, una vez por día. Con un número único o se le golpea la
 * puerta al portal ajeno seis veces más de lo necesario, o un mensaje llega
 * cuatro horas tarde. Lo que sí es uno solo es el lugar donde se ven.
 *
 * Tres fuentes comparten parámetro —facturas, cuenta corriente y órdenes salen
 * de la misma sección del portal—, y la tabla lo muestra tal cual en vez de
 * disimularlo: cambiar ese número mueve las tres, y quien lo cambia tiene que
 * verlo antes y no después.
 */
export function UpdateSources({ sources }: { sources: SyncSource[] }) {
  const router = useRouter()
  const [pidiendo, setPidiendo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pedida, setPedida] = useState<string | null>(null)

  async function traer(source: SyncSource) {
    setPidiendo(source.key)
    setError(null)
    setPedida(null)
    const result = await requestSync(source.key)
    setPidiendo(null)
    if (result.ok) {
      setPedida(source.label)
      router.refresh()
      return
    }
    setError(result.message)
  }

  return (
    <section className="space-y-3">
      {/*
        `TS-08`: lo que pasó con la última orden, dicho arriba de la tabla que la
        recibió. Una fuente ya corriendo vuelve con el mensaje del backend, que
        es el que sabe por qué.
      */}
      {error && (
        <Notice tone="danger" title="No se pudo pedir la actualización">
          {error}
        </Notice>
      )}
      {pedida && (
        <Notice tone="info" title={`Se pidió traer ${pedida.toLowerCase()}`}>
          Corre en segundo plano. Esta pantalla muestra cuándo terminó en cuanto la vuelvas a abrir.
        </Notice>
      )}

      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">
              Las fuentes de datos del portal, con cuándo se consultó cada una
            </caption>
            <thead>
              <tr className="border-b border-border">
                <th className="section-label px-4 py-3 text-left">Fuente</th>
                <th className="section-label px-4 py-3 text-left">Última consulta</th>
                <th className="section-label px-4 py-3 text-left">Próxima</th>
                <th className="section-label px-4 py-3 text-left">Frecuencia</th>
                <th className="px-4 py-3">
                  <span className="sr-only">Traer ahora</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sources.map(source => (
                <tr key={source.key} className="border-b border-border last:border-b-0">
                  <td className="px-4 py-3 font-medium text-foreground">{source.label}</td>

                  <td className="px-4 py-3">
                    {source.last_run_at === null ? (
                      <span className="text-muted-foreground">Todavía no se consultó nunca</span>
                    ) : (
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="amount text-[13px]">
                          {formatMoment(source.last_run_at)}
                        </span>
                        {source.last_run_status && (
                          <Badge tone={jobTone(source.last_run_status)}>
                            {getJobStatusLabel(source.last_run_status)}
                          </Badge>
                        )}
                      </span>
                    )}
                    {/*
                      Cuándo salió bien por última vez, **sólo cuando no es lo
                      mismo que la última corrida**. Una fuente que viene
                      fallando muestra su última corrida en rojo, y sin este
                      renglón no habría forma de saber desde cuándo los datos
                      que se están mirando son los de antes.
                    */}
                    {source.last_success_at !== null &&
                      source.last_success_at !== source.last_run_at && (
                        <span className="mt-0.5 block text-xs text-muted-foreground">
                          Última que salió bien: {formatMoment(source.last_success_at)}
                        </span>
                      )}
                  </td>

                  <td className="px-4 py-3">
                    {source.is_running ? (
                      <Badge tone="info">Corriendo ahora</Badge>
                    ) : source.next_due_at === null ? (
                      <span className="text-muted-foreground">En el próximo latido</span>
                    ) : (
                      <span className="amount text-[13px] text-muted-foreground">
                        {formatMoment(source.next_due_at)}
                      </span>
                    )}
                  </td>

                  <td className="px-4 py-3 text-muted-foreground">{cadaCuanto(source)}</td>

                  <td className="px-4 py-3 text-right">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={pidiendo !== null || source.is_running}
                      onClick={() => void traer(source)}
                    >
                      {pidiendo === source.key ? 'Pidiendo…' : 'Traer ahora'}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
