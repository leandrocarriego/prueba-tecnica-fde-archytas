'use client'

import * as Dialog from '@radix-ui/react-dialog'
import { cva, type VariantProps } from 'class-variance-authority'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

/**
 * La pregunta que hay que contestar antes de seguir.
 *
 * Existe para un solo caso y por eso no es un kit de diálogos: **cuando el
 * sistema no puede decidir solo y tiene que preguntar** (Artículo II de la
 * constitución, dicho en pantalla). Reemplaza al `window.confirm` nativo, que
 * tenía tres problemas y ninguno era estético:
 *
 * - **No se puede leer la pregunta entera.** El diálogo del navegador no formatea
 *   nada, así que la fecha a la que se está por mover —el dato sobre el que se
 *   decide— iba pegada en una línea de texto plano.
 * - **Lo bloquean los navegadores.** Un `confirm` en un iframe, o después de que
 *   la pestaña perdió el foco, no aparece: devuelve `false` sin preguntarle a
 *   nadie. Una confirmación que a veces no se muestra es peor que ninguna,
 *   porque el código cree que la persona dijo que no.
 * - **Congela el hilo.** Mientras está abierto no corre nada, ni el canal en
 *   vivo ni el `router.refresh()` de otra pestaña.
 *
 * No es un `Dialog` genérico a propósito: `Root/Portal/Overlay/Content/Title/
 * Description/Footer` es superficie que nadie pidió y siete formas de armar mal
 * el mismo diálogo. Acá se pasa la pregunta y las dos respuestas.
 *
 * Radix pone lo que no se ve y es lo caro de hacer bien: la trampa de foco, el
 * `Escape`, el `aria-modal` y el bloqueo del scroll de atrás.
 */
const markTone = cva(
  'flex size-8 flex-none items-center justify-center rounded-full text-sm font-bold',
  {
    variants: {
      tone: {
        warn: 'bg-brand text-brand-foreground',
        danger: 'bg-destructive text-destructive-foreground',
        info: 'bg-info text-white',
      },
    },
    defaultVariants: { tone: 'warn' },
  }
)

export interface ConfirmDialogProps extends VariantProps<typeof markTone> {
  open: boolean
  /** La pregunta, en una línea. Es lo que Radix usa para nombrar el diálogo. */
  title: string
  /** El detalle: sobre qué dato se está decidiendo. */
  children?: React.ReactNode
  /** Qué dice el botón que sigue adelante. Un verbo, no «Aceptar». */
  confirmLabel: string
  cancelLabel?: string
  /** Mientras la respuesta viaja, no se puede contestar dos veces. */
  busy?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  cancelLabel = 'Cancelar',
  tone,
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Dialog.Root
      open={open}
      // Cerrar por `Escape`, por el fondo o por la cruz es **decir que no**: la
      // única forma de seguir adelante es apretar el botón que lo dice.
      onOpenChange={next => {
        if (!next) onCancel()
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-foreground/40" />
        <Dialog.Content
          className={cn(
            'fixed left-1/2 top-1/2 z-50 w-[calc(100vw-2rem)] max-w-md -translate-x-1/2',
            '-translate-y-1/2 rounded-lg border bg-popover p-5 text-popover-foreground shadow-lg'
          )}
        >
          <div className="flex items-start gap-3">
            <span aria-hidden className={markTone({ tone })}>
              !
            </span>
            <div className="min-w-0 flex-1">
              <Dialog.Title className="text-base font-semibold leading-snug">{title}</Dialog.Title>
              {children ? (
                <Dialog.Description className="mt-1.5 text-sm text-muted-foreground">
                  {children}
                </Dialog.Description>
              ) : (
                /* Radix pide una descripción o que se diga que no hay. */
                <Dialog.Description className="sr-only">{title}</Dialog.Description>
              )}
            </div>
          </div>
          <div className="mt-5 flex flex-wrap justify-end gap-2">
            <Button type="button" variant="outline" onClick={onCancel}>
              {cancelLabel}
            </Button>
            {/*
              El acento de la pantalla, y va acá: mientras el diálogo está
              abierto, ésta **es** la decisión (`UI-05`).
            */}
            <Button type="button" variant="brand" disabled={busy} onClick={onConfirm}>
              {confirmLabel}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
