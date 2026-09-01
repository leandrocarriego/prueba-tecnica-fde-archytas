'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

import { saveParameter } from '@/app/actions/parameters'
import { Badge } from '@/components/ui/badge'
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
 * **Es una tarjeta**, y las tarjetas van en la grilla de la pantalla
 * (`docs/design/` 3m): un parámetro es una decisión chica y completa —qué hace,
 * entre qué valores, quién lo cambió— y en una lista de filas a lo ancho las
 * tres cosas quedaban lejos del campo que gobiernan.
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
export function ParameterCard({ parameter }: { parameter: Parameter }) {
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
    <form
      className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4 sm:p-5"
      onSubmit={onSubmit}
    >
      <div className="space-y-1.5">
        <div className="flex flex-wrap items-baseline gap-2">
          <label className="font-semibold" htmlFor={parameter.key}>
            {parameter.label}
          </label>
          {/* Es el estado del parámetro, así que es una píldora (`RF-06`). */}
          {!parameter.has_effect && (
            <Badge title="El valor se guarda y queda listo, pero todavía no hay ninguna funcionalidad que lo lea.">
              Todavía sin efecto
            </Badge>
          )}
        </div>
        <p className="text-sm text-muted-foreground">{parameter.effect}</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          id={parameter.key}
          className="amount w-32"
          type={isTime ? 'time' : 'number'}
          step={parameter.kind === 'DECIMAL' ? '0.01' : undefined}
          min={isTime ? undefined : bound(parameter.minimum)}
          max={isTime ? undefined : bound(parameter.maximum)}
          required
          value={value}
          onChange={event => setValue(event.target.value)}
        />
        {parameter.unit && <span className="text-sm text-muted-foreground">{parameter.unit}</span>}
        <Button type="submit" size="sm" className="ml-auto" disabled={saving || !changed}>
          {saving ? 'Guardando…' : 'Guardar'}
        </Button>
      </div>

      <p
        aria-live="polite"
        className={`text-sm ${message?.ok ? 'text-ok' : 'text-danger'}`}
        role="status"
      >
        {message?.text ?? ''}
      </p>

      {/*
        El rango y la procedencia van en una línea y el enlace en la otra: en
        una sola, el «Ver quién lo cambió» quedaba pegado al valor de fábrica y
        las tres cosas se leían como una frase sola.
      */}
      <div className="mt-auto space-y-0.5 text-xs text-muted-foreground">
        <p>
          <span className="amount">
            {isTime
              ? 'Entre 00:00 y 23:59'
              : `Entre ${String(parameter.minimum)} y ${String(parameter.maximum)}`}
          </span>
          {' · '}
          {parameter.changed_at ? 'lo cambiaste vos' : `de fábrica (${String(parameter.initial)})`}
        </p>
        <Link
          className="text-link underline-offset-2 hover:underline"
          href={`/historial?entidad=operations.parameter&id=${encodeURIComponent(parameter.key)}`}
        >
          Ver quién lo cambió y cuándo
        </Link>
      </div>
    </form>
  )
}
