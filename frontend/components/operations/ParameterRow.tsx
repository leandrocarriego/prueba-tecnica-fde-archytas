'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { saveParameter } from '@/app/actions/parameters'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { Parameter } from '@/lib/operations/types'

/**
 * One parameter of the system, with what it does and what it may be (RF-05).
 *
 * A Client Component because it is a field with state. Each row saves on its
 * own: a value the backend refuses says which row was wrong instead of failing
 * the whole panel, and the message it shows is the backend's, which is where
 * the range is decided (RF-06).
 *
 * The `min` and `max` on the input are a courtesy, never the rule. The refusal
 * is the API's, and the browser only spares the round trip.
 */
export function ParameterRow({ parameter }: { parameter: Parameter }) {
  const router = useRouter()
  const initial = String(parameter.value ?? '')
  const [value, setValue] = useState(initial)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)

  const isTime = parameter.kind === 'TIME_OF_DAY'
  const changed = value !== initial

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setMessage(null)

    const result = await saveParameter(parameter.key, value)
    setMessage(result.ok ? { ok: true, text: 'Guardado.' } : { ok: false, text: result.message })
    setSaving(false)
    if (result.ok) router.refresh()
  }

  return (
    <form className="space-y-2 border-t p-4 sm:p-5" onSubmit={onSubmit}>
      <div className="flex flex-wrap items-baseline gap-2">
        <label className="text-sm font-medium" htmlFor={parameter.key}>
          {parameter.label}
        </label>
        {!parameter.has_effect && (
          <span
            className="rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-700"
            title="El valor se guarda y queda listo, pero todavía no hay ninguna funcionalidad que lo lea."
          >
            Todavía sin efecto
          </span>
        )}
      </div>

      <p className="text-sm text-muted-foreground">{parameter.effect}</p>

      <div className="flex flex-wrap items-center gap-3">
        <Input
          id={parameter.key}
          className="w-40"
          type={isTime ? 'time' : 'number'}
          step={parameter.kind === 'DECIMAL' ? '0.01' : undefined}
          min={isTime ? undefined : ((parameter.minimum as string | null) ?? undefined)}
          max={isTime ? undefined : ((parameter.maximum as string | null) ?? undefined)}
          required
          value={value}
          onChange={event => setValue(event.target.value)}
        />
        {parameter.unit && <span className="text-sm text-muted-foreground">{parameter.unit}</span>}
        <Button type="submit" disabled={saving || !changed}>
          {saving ? 'Guardando…' : 'Guardar'}
        </Button>
        {message && (
          <p className={`text-sm ${message.ok ? 'text-emerald-700' : 'text-red-700'}`}>
            {message.text}
          </p>
        )}
      </div>

      <p className="text-xs text-muted-foreground">
        {isTime
          ? 'Una hora del día, entre 00:00 y 23:59.'
          : `Entre ${String(parameter.minimum)} y ${String(parameter.maximum)}.`}{' '}
        {parameter.changed_at
          ? 'Este valor lo cambiaste vos.'
          : `Es el valor con el que arranca el sistema (${String(parameter.initial)}).`}
      </p>
    </form>
  )
}
