'use client'

import * as React from 'react'
import { useState } from 'react'

/** Una barra: cuánto mide, cómo se rotula y cómo se lee el valor exacto. */
export interface Bar {
  key: string
  /** El rótulo del eje, ya abreviado por quien lo tiene. */
  label: string
  /** Lo que decide la altura. */
  value: number
  /** El valor exacto, ya formateado por quien sabe qué es (`<Money>`, `<Decimal>`). */
  reading: React.ReactNode
  /** El renglón de contexto de la tabla: cuántas ventas, cuántos cambios. */
  detail?: React.ReactNode
}

interface BarChartProps {
  bars: Bar[]
  /** Qué serie es, para quien la lee con un lector de pantalla. */
  caption: string
  /** El encabezado de la columna del valor: «Facturado», «Precio promedio». */
  valueLabel: string
  /** El encabezado de la columna de contexto, si las barras traen una. */
  detailLabel?: string
}

/**
 * A partir de cuántas barras el importe deja de entrar arriba de cada una.
 *
 * Con doce o menos hay lugar para escribirlo y se escribe: leer los doce meses
 * de un año de un vistazo es mejor que tener que recorrerlos con el mouse. Con
 * más —la serie completa arranca en 2023, que son más de cuarenta— los números
 * se pisarían, así que queda sólo el renglón de arriba.
 */
const CABEN_LOS_IMPORTES = 12

/**
 * Las barras de la guía visual (`3b`): tinta grafito sobre papel, sin ejes ni
 * grilla, con el rótulo del período abajo y una línea de base.
 *
 * **Cada barra dice cuánto vale.** Un gráfico sin números contesta «cómo viene
 * la cosa» y no contesta «cuánto», que es la pregunta con la que uno abre el
 * tablero. Se dice de dos maneras según lo que entre: con doce barras o menos,
 * el importe va escrito arriba de cada una; con más, hay un renglón sobre el
 * gráfico que muestra la barra que se está señalando —y sin señalar nada muestra
 * la última, que es el mes en curso y lo que casi siempre se vino a mirar.
 *
 * **Un gráfico no es el dato: es una forma de mirarlo.** Por eso las barras van
 * `aria-hidden` y debajo viaja la misma serie como tabla, visible sólo para
 * quien lee con un lector de pantalla. Una altura relativa no se puede leer en
 * voz alta, y un tablero que sólo se entiende mirándolo deja afuera a quien no
 * puede mirarlo. El renglón de arriba también es `aria-hidden` por lo mismo:
 * es la tabla dicha con el mouse, no un dato nuevo, y anunciarlo cada vez que
 * el puntero cruza una barra sería ruido sobre la misma serie que ya está.
 *
 * **Por qué la tabla y no un `title` en cada barra.** El texto del `title`
 * tendría que ser un string, y la plata de este producto sale de `<Money>`, no
 * de `money()` suelto (`UI-04`): la tabla y el renglón aceptan el elemento, el
 * atributo no.
 *
 * La barra tiene un ancho máximo: con tres meses en una tarjeta ancha, una
 * barra que ocupa su casillero entero deja de leerse como una barra y pasa a
 * ser un bloque. La guía las dibuja finas, y una serie corta no es una razón
 * para engordarlas.
 *
 * El eje se rotula salteado cuando la serie es larga —`RF-03` pide la
 * facturación desde 2023— porque doce rótulos que se leen valen más que
 * cuarenta encimados.
 */
export function BarChart({ bars, caption, valueLabel, detailLabel }: BarChartProps) {
  // Qué barra se está señalando. `null` es «ninguna», y entonces se lee la
  // última: un renglón vacío esperando que alguien pase el mouse desperdicia el
  // lugar que ocupa.
  const [señalada, setSeñalada] = useState<string | null>(null)

  const top = Math.max(...bars.map(bar => bar.value), 0)
  /** Cada cuántas barras se escribe un rótulo, para que entren. */
  const every = Math.ceil(bars.length / 12)
  const rotuladas = bars.length <= CABEN_LOS_IMPORTES
  const leyendo = bars.find(bar => bar.key === señalada) ?? bars.at(-1)

  return (
    <figure className="m-0">
      {/*
        El valor de la barra señalada. Sólo cuando los importes no entran arriba
        de cada una: con las dos cosas a la vez, el mismo número estaría escrito
        dos veces y una de las dos cambiaría al mover el mouse.
      */}
      {!rotuladas && leyendo && (
        <p aria-hidden className="mb-3 flex flex-wrap items-baseline gap-x-2">
          <span className="text-lg font-semibold text-foreground">{leyendo.reading}</span>
          <span className="text-xs text-muted-foreground">
            {leyendo.label}
            {leyendo.detail !== undefined && detailLabel !== undefined && (
              <>
                {` · ${detailLabel.toLowerCase()}: `}
                {leyendo.detail}
              </>
            )}
          </span>
        </p>
      )}

      <div
        aria-hidden
        className="flex h-40 items-end gap-1.5 border-b border-border pb-px"
        onMouseLeave={() => setSeñalada(null)}
      >
        {bars.map(bar => (
          <div
            key={bar.key}
            className="flex h-full flex-1 flex-col items-center justify-end"
            onMouseEnter={() => setSeñalada(bar.key)}
          >
            {rotuladas && (
              <span className="amount mb-1 text-[10px] text-muted-ink">{bar.reading}</span>
            )}
            <div
              className={`w-full max-w-16 rounded-t-[3px] transition-colors ${
                señalada !== null && señalada !== bar.key ? 'bg-muted-ink' : 'bg-primary'
              }`}
              /* La altura es proporción, no color: la paleta no la gobierna. */
              style={{ height: `${height(bar.value, top)}%` }}
            />
          </div>
        ))}
      </div>

      <div aria-hidden className="mt-2 flex gap-1.5">
        {bars.map((bar, index) => (
          <span key={bar.key} className="section-label flex-1 text-center">
            {index % every === 0 ? bar.label : ' '}
          </span>
        ))}
      </div>

      <table className="sr-only">
        <caption>{caption}</caption>
        <thead>
          <tr>
            <th scope="col">Período</th>
            <th scope="col">{valueLabel}</th>
            {detailLabel ? <th scope="col">{detailLabel}</th> : null}
          </tr>
        </thead>
        <tbody>
          {bars.map(bar => (
            <tr key={bar.key}>
              <th scope="row">{bar.label}</th>
              <td>{bar.reading}</td>
              {detailLabel ? <td>{bar.detail}</td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  )
}

/**
 * Qué porcentaje de la altura ocupa un valor.
 *
 * Un valor positivo nunca dibuja una barra de cero: un mes que facturó poco
 * facturó, y una barra invisible se lee como un mes sin ventas.
 */
function height(value: number, top: number): number {
  if (top <= 0 || value <= 0) return 0
  return Math.max((value / top) * 100, 2)
}
