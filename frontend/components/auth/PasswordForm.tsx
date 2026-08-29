'use client'

import { useState } from 'react'
import { useFormStatus } from 'react-dom'

import type { ActionResult } from '@/app/actions/access'

function SubmitButton({ label }: { label: string }) {
  const { pending } = useFormStatus()
  return (
    <button
      type="submit"
      disabled={pending}
      className="w-full cursor-pointer rounded bg-gray-900 px-4 py-2 text-white disabled:opacity-50"
    >
      {pending ? 'Guardando...' : label}
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
 *
 * `singleUse` says the action behind it can only succeed once, which is the
 * case for both links: the token is spent on use. Once it worked, the form goes
 * away. Leaving it on screen offers an action that can no longer succeed, and
 * somebody who presses it again reads "el enlace no sirve" and concludes their
 * password was never saved — the opposite of what happened.
 */
export function PasswordForm({
  action,
  label,
  asksCurrentPassword = false,
  singleUse = false,
}: {
  action: (formData: FormData) => Promise<ActionResult>
  label: string
  asksCurrentPassword?: boolean
  singleUse?: boolean
}) {
  const [result, setResult] = useState<ActionResult | null>(null)

  if (singleUse && result?.ok) {
    return <p className="text-sm text-green-700">{result.message}</p>
  }

  return (
    <form action={async formData => setResult(await action(formData))} className="space-y-3">
      {asksCurrentPassword && (
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

      <SubmitButton label={label} />

      {result && (
        <p className={`text-sm ${result.ok ? 'text-green-700' : 'text-red-700'}`}>
          {result.message}
        </p>
      )}
    </form>
  )
}
