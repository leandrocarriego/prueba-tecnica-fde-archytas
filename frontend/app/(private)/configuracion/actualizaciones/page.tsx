import { NoPermission } from '@/components/common/NoPermission'
import { ParameterCard } from '@/components/operations/ParameterCard'
import { UpdateSources } from '@/components/operations/UpdateSources'
import { Notice } from '@/components/ui/notice'
import { ErrorState } from '@/components/ui/state'
import { readFromApi } from '@/lib/api/server'
import type { Parameter, SyncSource } from '@/lib/operations/types'

export const metadata = {
  title: 'Actualizaciones — Plataforma Cordillera',
}

/**
 * Cada cuánto se consulta el portal, y cómo forzar una consulta.
 *
 * **Por qué existe esta pestaña.** Todo lo que la plataforma sabe lo trajo del
 * portal, y hasta acá cada extracción se administraba por su cuenta: cuatro
 * parámetros de frecuencia repartidos entre dieciséis tarjetas de «Parámetros»
 * —cada uno nombrado por lo suyo, así que la pantalla no decía en ningún lado
 * que los cuatro contestan la misma pregunta— y un único botón de «traerlo
 * ahora», el de la lista de precios, que existía sólo porque fue la primera
 * fuente que se construyó.
 *
 * **Los cuatro parámetros se mudaron acá desde «Parámetros».** RF-01 de la 003
 * pide que no haya parámetros escondidos dentro de la pantalla de la
 * funcionalidad que los usa, y eso se sigue cumpliendo: siguen estando en
 * Configuración, a una pestaña de distancia de los otros doce, y no dentro de
 * `/precios` ni de `/ventas`. Lo que cambió es que ahora están **al lado de la
 * fuente que gobiernan**, que es la única forma de que se entiendan.
 *
 * La lista de fuentes es la del backend, no una copia: los nombres, la unidad y
 * qué parámetro gobierna a cuál viajan con cada fila. Una segunda lista de este
 * lado sería una lista más para acordarse de actualizar el día que aparezca una
 * séptima fuente.
 */
export default async function UpdatesPage() {
  const [sources, parameters] = await Promise.all([
    readFromApi<SyncSource[]>('/operations/syncs'),
    readFromApi<Parameter[]>('/operations/parameters'),
  ])

  if (!sources.ok) {
    if (sources.failure === 'unauthorized') {
      return <NoPermission what="las actualizaciones del sistema" />
    }
    return (
      <ErrorState title="No pudimos traer el estado de las actualizaciones.">
        Probá de nuevo en unos minutos.
      </ErrorState>
    )
  }

  // Los parámetros que gobiernan una fuente, en el orden en que aparecen las
  // fuentes: es la lista del backend la que decide cuáles son, no una constante
  // escrita acá que habría que corregir cuando aparezca la séptima.
  const keys = [...new Set(sources.data.map(source => source.interval_key))]
  const all = parameters.ok ? parameters.data : []
  const intervals = keys
    .map(key => all.find(parameter => parameter.key === key))
    .filter((parameter): parameter is Parameter => parameter !== undefined)

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold">De dónde salen los datos</h2>
        <p className="text-sm text-muted-foreground">
          Todo lo que ves en la plataforma se lee del portal del proveedor. Acá está cada cosa que
          se trae, cuándo se trajo por última vez y cuándo vuelve a traerse.
        </p>
      </header>

      <UpdateSources sources={sources.data} />

      <section className="space-y-3">
        <header className="space-y-1">
          <h2 className="text-lg font-semibold">Cada cuánto se consulta</h2>
          <p className="text-sm text-muted-foreground">
            Un cambio rige desde la consulta siguiente, sin reiniciar nada. Cada valor se guarda
            solo.
          </p>
        </header>

        {/*
          Por qué no hay un número único para todo: los ritmos no son el mismo
          problema. Va escrito y no supuesto — es la pregunta que se hace
          cualquiera que abre esta pantalla.
        */}
        <Notice tone="info" title="Cada fuente tiene su propio ritmo, y conviene que lo tenga">
          Los mensajes se traen cada pocos minutos porque del otro lado hay alguien esperando una
          respuesta; las ventas, una vez por día. Un único número para las seis obligaría a elegir
          entre consultarle al portal mucho más de lo necesario o enterarse tarde de lo urgente.
        </Notice>

        {intervals.length === 0 ? (
          <ErrorState title="No pudimos traer los valores de frecuencia.">
            Las fuentes de arriba se siguen viendo, y «Traer ahora» sigue andando.
          </ErrorState>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {intervals.map(parameter => (
              <ParameterCard key={parameter.key} parameter={parameter} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
