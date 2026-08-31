'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

import { saveParameter } from '@/app/actions/parameters'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { Parameter } from '@/lib/operations/types'

/**
 * A bound as `min`/`max` can read it, or nothing at all.
 *
 * The generated schema types a bound `unknown`, and honestly so: what a
 * parameter's range is made of depends on what it measures — minutes, days, a
 * percentage, an hour of the day — and the API sends whatever that kind holds.
 * The attributes take a string or a number, so the question is asked rather
 * than asserted: an assertion here would promise the compiler a `string` for a
 * shape nobody checked, and React would hand the DOM the `[object Object]` it
 * stringifies to. That is not a number the browser can parse, so it drops the
 * bound and the courtesy below stops existing without a word — the same silence
 * this leaves, only chosen instead of stumbled into, and with no bound written
 * into the markup that means nothing. What refuses the value either way is the
 * API.
 */
function bound(value: unknown): string | number | undefined {
  return typeof value === 'string' || typeof value === 'number' ? value : undefined
}

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
 *
 * Each row links to its own history, because a parameter is a datum somebody
 * changed by hand like any other and RF-15 asks for the way back from **any**
 * of them. The kind and the identifier are the ones the log itself writes —
 * `operations.parameter` and the key — so the link answers instead of landing
 * on «esta pantalla no conoce ese dato».
 *
 * The verdict goes into a live region that is on the page from the start and
 * only changes its text. Whoever saves a parameter without seeing the screen
 * has nothing else to go on: the value in the field is the one they typed
 * whether it was accepted or refused, so «Guardado.» and the range the API
 * answers with are the entire difference between the two (RF-22, RF-06).
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
          min={isTime ? undefined : bound(parameter.minimum)}
          max={isTime ? undefined : bound(parameter.maximum)}
          required
          value={value}
          onChange={event => setValue(event.target.value)}
        />
        {parameter.unit && <span className="text-sm text-muted-foreground">{parameter.unit}</span>}
        <Button type="submit" disabled={saving || !changed}>
          {saving ? 'Guardando…' : 'Guardar'}
        </Button>
        <p
          aria-live="polite"
          className={`text-sm ${message?.ok ? 'text-emerald-700' : 'text-red-700'}`}
          role="status"
        >
          {message?.text ?? ''}
        </p>
      </div>

      <p className="text-xs text-muted-foreground">
        {isTime
          ? 'Una hora del día, entre 00:00 y 23:59.'
          : `Entre ${String(parameter.minimum)} y ${String(parameter.maximum)}.`}{' '}
        {parameter.changed_at
          ? 'Este valor lo cambiaste vos.'
          : `Es el valor con el que arranca el sistema (${String(parameter.initial)}).`}{' '}
        <Link
          className="underline underline-offset-2"
          href={`/historial?entidad=operations.parameter&id=${encodeURIComponent(parameter.key)}`}
        >
          Ver quién lo cambió y cuándo
        </Link>
      </p>
    </form>
  )
}
