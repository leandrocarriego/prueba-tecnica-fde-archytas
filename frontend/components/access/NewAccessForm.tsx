'use client'

import { useState } from 'react'
import { useFormStatus } from 'react-dom'

import { createAccess, type ActionResult } from '@/app/actions/access'
import { Button } from '@/components/ui/button'
import { Input, selectClassName } from '@/components/ui/input'
import { Notice } from '@/components/ui/notice'

/** Dar de alta es la tarea de esta pantalla: su único naranja (`RF-11`). */
function SubmitButton() {
  const { pending } = useFormStatus()
  return (
    <Button type="submit" variant="brand" disabled={pending}>
      {pending ? 'Dando de alta…' : 'Dar de alta e invitar'}
    </Button>
  )
}

/**
 * The form that hands out an access.
 *
 * There is no password field, and that is the feature: the person sets their
 * own from the invitation, so the owner never knows it (RF-44).
 *
 * No trae tarjeta ni título propios: se abre **adentro** de la tarjeta de
 * accesos, debajo del botón que lo pidió, y quien lo abrió ya sabe qué está
 * haciendo (`docs/design/` 3m).
 */
export function NewAccessForm({ onCreated }: { onCreated?: (message: string) => void }) {
  const [result, setResult] = useState<ActionResult | null>(null)

  return (
    <form
      action={async formData => {
        const outcome = await createAccess(formData)
        // El alta que sale bien la cuenta el panel, que es el que sigue en
        // pantalla cuando este formulario se cierra; acá queda sólo el rechazo,
        // que hay que leer al lado del campo que lo provocó.
        if (outcome.ok) onCreated?.(outcome.message)
        setResult(outcome.ok ? null : outcome)
      }}
      className="space-y-3"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Input name="name" required placeholder="Nombre" aria-label="Nombre" />
        <Input name="last_name" placeholder="Apellido" aria-label="Apellido" />
        <Input
          name="email"
          type="email"
          required
          placeholder="Correo con el que entra"
          aria-label="Correo con el que entra"
        />
        <Input
          name="phone"
          required
          className="amount"
          placeholder="+54 9 261 555 1234"
          aria-label="Teléfono, completo como aparece en WhatsApp"
          aria-describedby="phone-help"
        />
        <select name="role" defaultValue="SALES" className={selectClassName} aria-label="Rol">
          <option value="PURCHASING">Compras</option>
          <option value="SALES">Ventas</option>
        </select>
      </div>

      <p className="text-xs text-muted-foreground" id="phone-help">
        La invitación le llega por WhatsApp, así que el teléfono va{' '}
        <strong className="font-semibold">completo, tal como aparece en WhatsApp</strong> — con el
        código de país y el de área. No le pongas una clave: la elige ella desde la invitación.
      </p>

      <SubmitButton />

      {result && <Notice tone={result.ok ? 'ok' : 'danger'} title={result.message} />}
    </form>
  )
}
