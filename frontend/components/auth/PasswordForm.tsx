'use client'

import { useState } from 'react'
import { useFormStatus } from 'react-dom'

import type { ActionResult } from '@/app/actions/access'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Notice } from '@/components/ui/notice'

/**
 * Guardar la clave es la tarea de las tres pantallas que usan este formulario,
 * así que es el naranja de cada una (`RF-11`).
 */
function SubmitButton({ label }: { label: string }) {
  const { pending } = useFormStatus()
  return (
    <Button type="submit" variant="brand" disabled={pending} className="w-full">
      {pending ? 'Guardando…' : label}
    </Button>
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
    return <Notice tone="ok" title={result.message} />
  }

  return (
    <form action={async formData => setResult(await action(formData))} className="space-y-3">
      {asksCurrentPassword && (
        <Input
          name="current_password"
          type="password"
          required
          placeholder="Tu clave de ahora"
          aria-label="Tu clave de ahora"
        />
      )}
      <Input
        name="new_password"
        type="password"
        required
        minLength={8}
        placeholder="Clave nueva"
        aria-label="Clave nueva"
      />
      <Input
        name="repeat_password"
        type="password"
        required
        minLength={8}
        placeholder="Repetí la clave nueva"
        aria-label="Repetí la clave nueva"
      />
      <p className="text-xs text-muted-foreground">Al menos 8 caracteres.</p>

      <SubmitButton label={label} />

      {/* Lo que contestó el servidor: verde si guardó, rojo si no. */}
      {result && <Notice tone={result.ok ? 'ok' : 'danger'} title={result.message} />}
    </form>
  )
}
