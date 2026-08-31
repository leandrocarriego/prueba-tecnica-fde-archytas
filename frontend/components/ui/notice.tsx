import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

/**
 * El aviso de la guía visual: **el sistema no adivina, informa qué quedó afuera
 * y por qué, con una acción para resolverlo** (Artículo II de la constitución,
 * dicho en pantalla).
 *
 * Por eso la franja va *antes* que los números que resume, no al pie: primero
 * se dice si se puede confiar en los datos, después se muestran.
 */
const noticeVariants = cva('rounded-lg border p-3.5 text-sm', {
  variants: {
    tone: {
      warn: 'border-warn-border bg-warn-surface text-foreground',
      danger: 'border-danger-border bg-danger-surface text-foreground',
      info: 'border-info-border bg-info-surface text-foreground',
      ok: 'border-ok-border bg-ok-surface text-foreground',
    },
  },
  defaultVariants: { tone: 'warn' },
})

const MARK_TONE = {
  warn: 'bg-brand text-brand-foreground',
  danger: 'bg-destructive text-destructive-foreground',
  info: 'bg-info text-white',
  ok: 'bg-ok text-white',
} as const

export interface NoticeProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof noticeVariants> {
  title: string
  /** La acción que resuelve el aviso. Un aviso sin salida es sólo una queja. */
  action?: React.ReactNode
}

export function Notice({ className, tone, title, action, children, ...props }: NoticeProps) {
  const mark = MARK_TONE[tone ?? 'warn']

  return (
    <div className={cn(noticeVariants({ tone }), className)} {...props}>
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className={cn(
            'mt-0.5 flex size-5 flex-none items-center justify-center rounded-full text-xs font-bold',
            mark
          )}
        >
          !
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-semibold leading-snug">{title}</p>
          {children ? <div className="mt-1 text-muted-foreground">{children}</div> : null}
        </div>
        {action ? <div className="flex-none">{action}</div> : null}
      </div>
    </div>
  )
}
