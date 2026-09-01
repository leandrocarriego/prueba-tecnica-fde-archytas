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
 */
export function NewAccessForm() {
  const [result, setResult] = useState<ActionResult | null>(null)

  return (
    <form
      action={async formData => setResult(await createAccess(formData))}
      className="space-y-3 rounded-lg border border-border bg-card p-5"
    >
      <h2 className="font-medium">Dar de alta a alguien</h2>

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
          placeholder="Teléfono, con código de país"
          aria-label="Teléfono, con código de país"
        />
        <select name="role" defaultValue="SALES" className={selectClassName} aria-label="Rol">
          <option value="PURCHASING">Compras</option>
          <option value="SALES">Ventas</option>
        </select>
      </div>

      <p className="text-xs text-muted-foreground">
        No le pongas una clave: le va a llegar una invitación por WhatsApp para que la elija ella.
      </p>

      <SubmitButton />

      {result && <Notice tone={result.ok ? 'ok' : 'danger'} title={result.message} />}
    </form>
  )
}
