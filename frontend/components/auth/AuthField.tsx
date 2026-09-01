import * as React from 'react'

import { Input, type InputProps } from '@/components/ui/input'

interface AuthFieldProps extends InputProps {
  id: string
  label: string
}

/**
 * Un campo de las pantallas de sesión: el rótulo arriba, en mono versalita.
 *
 * Existe para que los cinco campos que hay entre el ingreso y la recuperación
 * se dibujen igual. El rótulo usa `.section-label`, que es la etiqueta de la
 * guía —mono, versalita, muy espaciada—: la misma que nombra un bloque en el
 * resto de la plataforma.
 */
export function AuthField({ id, label, ...props }: AuthFieldProps) {
  return (
    <div className="space-y-1.5">
      <label className="section-label block" htmlFor={id}>
        {label}
      </label>
      <Input id={id} {...props} />
    </div>
  )
}
