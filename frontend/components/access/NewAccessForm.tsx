'use client'

import { useState } from 'react'
import { useFormStatus } from 'react-dom'

import { createAccess, type ActionResult } from '@/app/actions/access'

function SubmitButton() {
  const { pending } = useFormStatus()
  return (
    <button
      type="submit"
      disabled={pending}
      className="cursor-pointer rounded bg-primary px-4 py-2 text-white disabled:opacity-50"
    >
      {pending ? 'Dando de alta...' : 'Dar de alta e invitar'}
    </button>
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
      className="space-y-3 rounded border p-4"
    >
      <h2 className="font-medium">Dar de alta a alguien</h2>

      <div className="grid gap-3 sm:grid-cols-2">
        <input name="name" required placeholder="Nombre" className="rounded border px-3 py-2" />
        <input name="last_name" placeholder="Apellido" className="rounded border px-3 py-2" />
        <input
          name="email"
          type="email"
          required
          placeholder="Correo con el que entra"
          className="rounded border px-3 py-2"
        />
        <input
          name="phone"
          required
          placeholder="Teléfono, con código de país"
          className="rounded border px-3 py-2"
        />
        <select name="role" defaultValue="SALES" className="rounded border px-3 py-2">
          <option value="PURCHASING">Compras</option>
          <option value="SALES">Ventas</option>
        </select>
      </div>

      <p className="text-xs text-muted-foreground">
        No le pongas una clave: le va a llegar una invitación por WhatsApp para que la elija ella.
      </p>

      <SubmitButton />

      {result && (
        <p className={`text-sm ${result.ok ? 'text-ok' : 'text-danger'}`}>{result.message}</p>
      )}
    </form>
  )
}
