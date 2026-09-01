import * as React from 'react'

import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

/**
 * Las tres caras que tiene cualquier pantalla antes de tener datos: **cargando,
 * con error y sin resultados** (`RF-19`).
 *
 * Existen porque hoy no existe ninguna: cada pantalla improvisa su «Cargando…»,
 * su recuadro rojo y su «No hay nada», y las tres se ven distintas en cada una.
 * Para quien trabaja, esa diferencia no es estética: es tener que aprender de
 * nuevo, en cada sección, si lo que está viendo es un problema o simplemente no
 * hay nada.
 *
 * Las tres comparten forma —tarjeta, texto centrado, un renglón de explicación
 * y a lo sumo una acción— y se distinguen por lo que dicen, no por el color.
 * Ninguna usa el naranja: no son decisiones, son estados (`RF-07`).
 */

interface StateProps {
  /** El renglón principal. Corto: lo que pasó, no por qué. */
  title: string
  /** La explicación, cuando hay algo útil que decir. */
  children?: React.ReactNode
  /** La salida, si la hay. Un aviso sin salida es sólo una queja. */
  action?: React.ReactNode
  className?: string
}

function Frame({ title, children, action, className, ...props }: StateProps & { role?: string }) {
  return (
    <Card className={cn('px-6 py-12 text-center', className)} {...props}>
      <p className="font-semibold">{title}</p>
      {children ? <div className="mt-1.5 text-sm text-muted-foreground">{children}</div> : null}
      {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
    </Card>
  )
}

/**
 * La pantalla está esperando al servidor.
 *
 * Sin animación de color y sin spinner de marca: tres barras que laten. Lo que
 * tiene que comunicar es «esto todavía no es el dato», y para eso alcanza con
 * que no se parezca a una tabla vacía.
 */
export function Loading({ what }: { what?: string }) {
  return (
    <Card className="p-6" role="status" aria-busy="true">
      <span className="sr-only">{what ? `Cargando ${what}…` : 'Cargando…'}</span>
      <div className="animate-pulse space-y-3" aria-hidden>
        <div className="h-4 w-1/3 rounded bg-secondary" />
        <div className="h-4 w-full rounded bg-secondary" />
        <div className="h-4 w-4/5 rounded bg-secondary" />
      </div>
    </Card>
  )
}

/**
 * Algo salió mal, y no es culpa de quien mira.
 *
 * `title` dice qué no se pudo hacer en la lengua del negocio —«No pudimos traer
 * las facturas»—, nunca el código de error: quien lee esto no puede hacer nada
 * con un 502, y sí puede volver a intentar en un rato.
 */
export function ErrorState({ title, children, action, className }: StateProps) {
  return (
    <Frame
      role="alert"
      title={title}
      action={action}
      className={cn('border-danger-border bg-danger-surface', className)}
    >
      {children ?? 'Probá de nuevo en unos minutos.'}
    </Frame>
  )
}

/**
 * No hay nada que mostrar, y eso **no** es un error.
 *
 * Por eso no lleva el fondo del error ni ningún color de estado: una cola de
 * revisión vacía es la mejor noticia del día, y pintarla de rojo enseñaría lo
 * contrario.
 */
export function Empty({ title, children, action, className }: StateProps) {
  return (
    <Frame title={title} action={action} className={className}>
      {children}
    </Frame>
  )
}
