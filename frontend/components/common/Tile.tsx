import * as React from 'react'

interface TileProps {
  /** El rótulo, en versalita. Nombra el número sin competir con él. */
  label: string
  value: React.ReactNode
  /** El renglón de contexto: qué compone el número, o qué hacer con él. */
  sub: React.ReactNode
  /** La tarjeta que pide una decisión: borde y rótulo ámbar. */
  accent?: boolean
}

/**
 * Una de las tarjetas de arriba del tablero (guía visual `3b`).
 *
 * Vive en `common/` y no en un dominio porque la fila las mezcla: el facturado
 * es de ventas, la deuda y los vencimientos son de compras, y la guía las dibuja
 * iguales a propósito —cuatro cuentas del mismo tamaño, leídas de un vistazo—.
 * Dos copias de esta tarjeta serían dos tipografías del mismo número.
 *
 * El acento ámbar significa lo que significa en toda la aplicación: **esto
 * espera una decisión de una persona**. Por eso lo decide quien la usa y en
 * general sólo cuando el número no es cero: una tarjeta pintada de ámbar con un
 * cero enseña que el color no quiere decir nada.
 */
export function Tile({ label, value, sub, accent }: TileProps) {
  return (
    <div
      className={`min-w-56 flex-1 rounded-xl border bg-card p-4 ${
        accent ? 'border-warn-border' : 'border-border'
      }`}
    >
      <div className={`section-label ${accent ? 'text-warn' : ''}`}>{label}</div>
      <div className="amount mt-2 text-2xl font-medium text-foreground">{value}</div>
      <div className="mt-2 text-xs text-muted-foreground">{sub}</div>
    </div>
  )
}
