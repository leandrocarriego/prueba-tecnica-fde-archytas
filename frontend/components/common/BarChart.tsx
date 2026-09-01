import * as React from 'react'

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
 * Las barras de la guía visual (`3b`): tinta grafito sobre papel, sin ejes ni
 * grilla, con el rótulo del período abajo y una línea de base.
 *
 * **Un gráfico no es el dato: es una forma de mirarlo.** Por eso las barras van
 * `aria-hidden` y debajo viaja la misma serie como tabla, visible sólo para
 * quien lee con un lector de pantalla. Una altura relativa no se puede leer en
 * voz alta, y un tablero que sólo se entiende mirándolo deja afuera a quien no
 * puede mirarlo.
 *
 * **Por qué la tabla y no un `title` en cada barra.** El texto del `title`
 * tendría que ser un string, y la plata de este producto sale de `<Money>`, no
 * de `money()` suelto (`UI-04`): la tabla acepta el elemento, el atributo no.
 *
 * La barra tiene un ancho máximo: con tres meses en una tarjeta ancha, una
 * barra que ocupa su casillero entero deja de leerse como una barra y pasa a
 * ser un bloque. La guía las dibuja finas, y una serie corta no es una razón
 * para engordarlas.
 *
 * El eje se rotula salteado cuando la serie es larga —`RF-03` pide la
 * facturación desde 2023, que son más de cuarenta barras— porque doce rótulos
 * que se leen valen más que cuarenta encimados.
 */
export function BarChart({ bars, caption, valueLabel, detailLabel }: BarChartProps) {
  const top = Math.max(...bars.map(bar => bar.value), 0)
  /** Cada cuántas barras se escribe un rótulo, para que entren. */
  const every = Math.ceil(bars.length / 12)

  return (
    <figure className="m-0">
      <div aria-hidden className="flex h-40 items-end gap-1.5 border-b border-border pb-px">
        {bars.map(bar => (
          <div key={bar.key} className="flex h-full flex-1 items-end justify-center">
            <div
              className="w-full max-w-16 rounded-t-[3px] bg-primary"
              /* La altura es proporción, no color: la paleta no la gobierna. */
              style={{ height: `${height(bar.value, top)}%` }}
            />
          </div>
        ))}
      </div>

      <div aria-hidden className="mt-2 flex gap-1.5">
        {bars.map((bar, index) => (
          <span key={bar.key} className="section-label flex-1 text-center">
            {index % every === 0 ? bar.label : ' '}
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
