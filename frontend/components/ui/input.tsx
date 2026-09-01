import * as React from 'react'

import { cn } from '@/lib/utils'

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        'flex h-10 w-full rounded-md border border-input bg-card px-3 py-2 text-sm',
        'ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium',
        'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2',
        'focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed',
        'disabled:opacity-50',
        className
      )}
      ref={ref}
      {...props}
    />
  )
)
Input.displayName = 'Input'

/**
 * La forma de un `<select>` nativo, que es la misma que la del campo de texto.
 *
 * No hay componente porque no hace falta: un `select` con sus `option` ya es el
 * control que el navegador sabe dibujar mejor —y en un teléfono, el único que
 * se usa cómodo—. Lo que sí tiene que ser uno solo es su aspecto, y por eso la
 * clase vive acá y no copiada en las nueve pantallas que filtran algo.
 */
export const selectClassName = cn(
  'flex h-10 w-full rounded-md border border-input bg-card px-3 py-2 text-sm',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
  'focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50'
)

export { Input }
