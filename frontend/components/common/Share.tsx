import * as React from 'react'

interface ShareProps {
  label: string
  /** El número, ya formateado por quien sabe qué es: una cuenta, un importe. */
  reading: React.ReactNode
  /** Qué parte del total ocupa, de 0 a 100. */
  share: number
  /** La porción que se mide pero **no está sumada** en el dato de al lado. */
  excluded?: boolean
}

/**
 * Un renglón de una composición: el rótulo, el número a la derecha y la barra
 * debajo (guía visual `3b`, el panel de «gasto por rubro»).
 *
 * Existe una sola vez porque el tablero la usa dos veces —el gasto por rubro y
 * la cobertura del corte de stock— y dos copias de una barra de composición son
 * dos maneras de dibujar la misma pregunta.
 *
 * Todas las barras van en tinta y ninguna en color: el orden y el largo ya
 * dicen cuál es más grande, y una escala de colores le daría a cada rubro un
 * significado que no tiene. El único relleno distinto es el rayado, que sí
 * significa algo: eso no está sumado.
 */
export function Share({ label, reading, share, excluded }: ShareProps) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 text-[13px]">
        <span className={excluded ? 'text-warn' : 'text-foreground'}>{label}</span>
        <span className="amount text-foreground">{reading}</span>
      </div>
      <div className="mt-1.5 h-[7px] rounded-full bg-muted">
        <div
          className={`h-full rounded-full ${excluded ? 'hatch-excluded' : 'bg-primary'}`}
          /* Una proporción, no un color: la paleta no la gobierna. */
          style={{ width: `${Math.min(Math.max(share, 0), 100)}%` }}
        />
      </div>
    </div>
  )
}
