'use client'

import { useState } from 'react'
import { useFormStatus } from 'react-dom'

import type { ActionResult } from '@/app/actions/access'

function Enviar({ etiqueta }: { etiqueta: string }) {
  const { pending } = useFormStatus()
  return (
    <button
      type="submit"
      disabled={pending}
      className="w-full cursor-pointer rounded bg-gray-900 px-4 py-2 text-white disabled:opacity-50"
    >
      {pending ? 'Guardando...' : etiqueta}
    </button>
  )
}

/**
 * The one form behind setting a password, wherever it is being set.
 *
 * Changing your own, redeeming an invitation and using a recovery link all ask
 * for the same thing and repeat it back, so they are one component with a
 * different action. The only difference is whether the current password is
 * asked for, and that is the point: from a link there is nothing to ask.
 */
export function PasswordForm({
  action,
  etiqueta,
  pideClaveActual = false,
}: {
  action: (formData: FormData) => Promise<ActionResult>
  etiqueta: string
  pideClaveActual?: boolean
}) {
  const [result, setResult] = useState<ActionResult | null>(null)

  return (
    <form action={async formData => setResult(await action(formData))} className="space-y-3">
      {pideClaveActual && (
        <input
          name="current_password"
          type="password"
          required
          placeholder="Tu clave de ahora"
          className="w-full rounded border px-3 py-2"
        />
      )}
      <input
        name="new_password"
        type="password"
        required
        minLength={8}
        placeholder="Clave nueva"
        className="w-full rounded border px-3 py-2"
      />
      <input
        name="repeat_password"
        type="password"
        required
        minLength={8}
        placeholder="Repetí la clave nueva"
        className="w-full rounded border px-3 py-2"
      />
      <p className="text-xs text-muted-foreground">Al menos 8 caracteres.</p>

      <Enviar etiqueta={etiqueta} />

      {result && (
        <p className={`text-sm ${result.ok ? 'text-green-700' : 'text-red-700'}`}>
          {result.message}
        </p>
      )}
    </form>
  )
}
