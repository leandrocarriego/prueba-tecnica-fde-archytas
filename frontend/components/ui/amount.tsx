import * as React from 'react'

import { day, decimal, money } from '@/lib/format'
import { cn } from '@/lib/utils'

/**
 * La plata, las fechas y los códigos, escritos siempre igual (`RF-09`, `RF-10`,
 * `UI-04`).
 *
 * **Por qué un componente y no una convención.** `money()` devuelve un string, y
 * quien lo escribe elige con qué tipografía sale: por eso hoy el mismo importe
 * se dibuja en mono en una pantalla y en la tipografía de texto en la de al
 * lado, y por eso una columna de importes de cuatro y de siete dígitos no
 * alinea sus comas. Un componente no deja elegir: el valor sale envuelto en
 * `.amount` —mono tabular— o no sale.
 *
 * **El formateo no se mudó acá.** Sigue en `lib/format.ts`, que es lo que este
 * archivo usa: hay catorce lugares que necesitan el *string* y no el elemento
 * —un `title`, un `aria-label`, el asunto de un mensaje— y partir el formateo
 * en dos sería exactamente el problema que `lib/format.ts` vino a resolver.
 *
 * **`cell` es la mitad que importa en una tabla.** Una columna de importes se
 * lee cuando las unidades caen en la misma vertical, y eso es alineación a la
 * derecha, no tipografía: `<Money value={x} cell />` dibuja el `<td>` ya
 * alineado, y así la pantalla no puede olvidárselo en la fila del total.
 */

type Element = 'span' | 'td' | 'th' | 'dd' | 'div'

interface BaseProps extends React.HTMLAttributes<HTMLElement> {
  /** Dibuja un `<td>` alineado a la derecha, en vez de un `<span>`. */
  cell?: boolean
  /** El elemento, cuando no es ninguno de los dos anteriores. */
  as?: Element
}

/** El envoltorio común: quién dibuja, con qué clases, y el valor ya formateado. */
function Value({ cell, as, className, children, ...props }: BaseProps) {
  const Tag: Element = as ?? (cell ? 'td' : 'span')
  return React.createElement(
    Tag,
    { className: cn('amount', cell && 'text-right', className), ...props },
    children
  )
}

interface NumberProps extends BaseProps {
  value: string | number | null | undefined
}

/** Un importe en pesos. Sin valor escribe «—», que es lo que hace `money()`. */
export function Money({ value, ...props }: NumberProps) {
  return <Value {...props}>{money(value)}</Value>
}

/** Un número con a lo sumo un decimal: un promedio de días, un porcentaje. */
export function Decimal({ value, ...props }: NumberProps) {
  return <Value {...props}>{decimal(value)}</Value>
}

/** Un día del negocio: un vencimiento, la fecha de una factura, la de una venta. */
export function Day({ value, ...props }: BaseProps & { value: string | null | undefined }) {
  return <Value {...props}>{day(value)}</Value>
}

/**
 * Un código que se compara de un vistazo: el número de una factura, el de una
 * orden, el código de un producto. Va en mono por la misma razón que la plata
 * —dos códigos parecidos se distinguen cuando los dígitos alinean—, pero no se
 * formatea: se muestra tal cual llegó.
 */
export function Code({
  value,
  children,
  ...props
}: BaseProps & { value?: string | null | undefined }) {
  return <Value {...props}>{value ?? children ?? '—'}</Value>
}
