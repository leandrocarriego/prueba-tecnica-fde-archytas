import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

/**
 * La píldora de estado de la guía visual (`docs/design/`).
 *
 * Existe para decir **en qué estado está un dato** —saldada, parcial, vencida,
 * sin confirmar—, y para nada más: una píldora de adorno gasta el único recurso
 * con el que la pantalla avisa que algo requiere una decisión.
 *
 * Los estilos viven en `app/globals.css` (`.pill`, `.pill-ok`, …) porque los
 * usan también las tablas, que arman sus celdas sin pasar por React.
 */
const badgeVariants = cva('pill', {
  variants: {
    tone: {
      neutral: '',
      ok: 'pill-ok',
      info: 'pill-info',
      warn: 'pill-warn',
      danger: 'pill-danger',
      /** Leído del origen pero todavía sin confirmar por una persona. */
      draft: 'pill-draft',
    },
  },
  defaultVariants: { tone: 'neutral' },
})

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />
}

export { badgeVariants }
