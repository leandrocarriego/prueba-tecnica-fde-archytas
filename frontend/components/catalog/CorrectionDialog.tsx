'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { correctProduct } from '@/app/actions/corrections'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { CorrectionReason } from '@/lib/operations/types'

interface CorrectionDialogProps {
  productId: number
  field: string
  fieldLabel: string
  currentValue: string
  reasons: CorrectionReason[]
  /** Numbers get a numeric field; a description does not. */
  numeric?: boolean
}

/** How the last attempt went, wherever it has to be read. */
function Outcome({ ok, text }: { ok: boolean; text: string }) {
  return <span className={`text-sm ${ok ? 'text-emerald-700' : 'text-red-700'}`}>{text}</span>
}

/**
 * Correcting one value, with the reason the business asks for (RF-11).
 *
 * A Client Component: it is a form that opens, validates and reports back.
 *
 * The reasons are handed in rather than fetched here, and they came from the
 * API: it is the backend that refuses an unknown `reason_code`, so the list
 * offered and the list accepted are the same one. A copy in the browser would
 * be the second list that eventually offers something the API rejects.
 *
 * Whether it worked is shown right here (RF-22). A refusal shows the backend's
 * own message — it is the one that knows why — and leaves the form open, over
 * the value it refused, which is where it has to be corrected.
 *
 * A correction that went through closes the form, and the outcome is rendered
 * from the closed branch too. That is deliberate and it is the whole rule: the
 * form and the verdict are two different things, and only the form is worth
 * hiding. Whoever is fixing ten prices in a row wants the next field one click
 * away, not a form to dismiss — and reads that the last one was applied right
 * beside the button they are about to press again. Writing the message and
 * closing in the same run, with only the form rendered while closed, is the
 * one combination that leaves them with nothing to read.
 */
export function CorrectionDialog({
  productId,
  field,
  fieldLabel,
  currentValue,
  reasons,
  numeric = false,
}: CorrectionDialogProps) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [value, setValue] = useState(currentValue)
  const [reasonCode, setReasonCode] = useState(reasons[0]?.code ?? '')
  const [detail, setDetail] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)

  if (!open) {
    return (
      <span className="inline-flex flex-wrap items-center gap-3">
        <button
          className="cursor-pointer text-sm underline underline-offset-2"
          onClick={() => {
            setOpen(true)
            // The verdict of the previous correction is cleared on the way in:
            // «Corregido» sitting over a value being edited now would be read as
            // this one having been applied.
            setMessage(null)
          }}
          type="button"
        >
          Corregir {fieldLabel}
        </button>
        {message && <Outcome ok={message.ok} text={message.text} />}
      </span>
    )
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setMessage(null)

    const result = await correctProduct({
      productId,
      field,
      value,
      reasonCode,
      reasonDetail: detail,
    })
    setSaving(false)

    if (!result.ok) {
      setMessage({ ok: false, text: result.message })
      return
    }
    setMessage({ ok: true, text: 'Corregido. Queda registrado quién lo cambió y por qué.' })
    setOpen(false)
    setDetail('')
    router.refresh()
  }

  return (
    <form className="space-y-4 rounded border bg-white p-4" onSubmit={onSubmit}>
      <p className="text-sm font-medium">Corregir {fieldLabel}</p>

      <div className="space-y-1">
        <label className="block text-sm" htmlFor={`value-${field}`}>
          Valor correcto
        </label>
        <Input
          id={`value-${field}`}
          type={numeric ? 'number' : 'text'}
          step={numeric ? '0.01' : undefined}
          required
          value={value}
          onChange={event => setValue(event.target.value)}
        />
      </div>

      <div className="space-y-1">
        <label className="block text-sm" htmlFor={`reason-${field}`}>
          Motivo
        </label>
        <select
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          id={`reason-${field}`}
          required
          value={reasonCode}
          onChange={event => setReasonCode(event.target.value)}
        >
          {reasons.map(reason => (
            <option key={reason.code} value={reason.code}>
              {reason.label}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-1">
        <label className="block text-sm" htmlFor={`detail-${field}`}>
          Detalle (opcional)
        </label>
        <Input
          id={`detail-${field}`}
          type="text"
          maxLength={1000}
          placeholder="Lo que haga falta aclarar"
          value={detail}
          onChange={event => setDetail(event.target.value)}
        />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={saving || !reasonCode}>
          {saving ? 'Guardando…' : 'Corregir'}
        </Button>
        <button
          className="cursor-pointer text-sm text-muted-foreground underline"
          onClick={() => {
            setOpen(false)
            setMessage(null)
          }}
          type="button"
        >
          Cancelar
        </button>
        {message && <Outcome ok={message.ok} text={message.text} />}
      </div>
    </form>
  )
}
