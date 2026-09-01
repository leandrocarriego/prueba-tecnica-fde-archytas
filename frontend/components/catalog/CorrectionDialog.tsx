'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { correctProduct } from '@/app/actions/corrections'
import { Button } from '@/components/ui/button'
import { Input, selectClassName } from '@/components/ui/input'
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

/**
 * How the last attempt went, wherever it has to be read.
 *
 * Rendered once, outside the half that opens and closes, and that placement is
 * the point: the region has to be the same node before and after the verdict is
 * written into it. A live region that arrives on the page already holding its
 * first message is announced by some readers and skipped by others, and the
 * successful correction is exactly where that would happen — `setMessage` and
 * `setOpen(false)` are batched into one render, so a region living inside the
 * closed half would be mounted with the confirmation already inside it. RF-22
 * has to answer whoever cannot see the colour the message is written in, which
 * is the same person who cannot see that the form closed either.
 *
 * It is the last child of the wrapper, so when it is empty all it adds is a
 * trailing gap nobody can see.
 */
function Outcome({ message }: { message: { ok: boolean; text: string } | null }) {
  return (
    <p
      aria-live="polite"
      className={`text-sm ${message?.ok ? 'text-ok' : 'text-danger'}`}
      role="status"
    >
      {message?.text ?? ''}
    </p>
  )
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
 * A correction that went through closes the form, and the verdict does not move
 * with it: only the form is worth hiding, so only the form is what the branch
 * below switches. Whoever is fixing ten prices in a row wants the next field
 * one click away, not a form to dismiss — and reads that the last one was
 * applied right beside the button they are about to press again. Writing the
 * message and closing in the same run, with the verdict rendered from inside
 * the form, is the one combination that leaves them with nothing to read.
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

  /**
   * Everything that was typed and never confirmed, thrown away.
   *
   * Cancelling abandons the edit, so it abandons everything chosen inside it:
   * the value goes back to what the datum holds, the detail is dropped, and the
   * reason returns to the top of the list. Closing without this made «Cancelar»
   * a way of hiding the form rather than of abandoning the edit — reopen it and
   * the abandoned text is sitting in the field, indistinguishable from something
   * just written, one click away from being saved with a reason nobody chose for
   * it.
   *
   * The successful run deliberately does not call it. There the typed value is
   * what the datum now holds, while `currentValue` is still the value from
   * before the correction until `router.refresh()` brings the new one — putting
   * it back would leave the field showing the very price that was just
   * corrected away.
   */
  function discardDraft() {
    setValue(currentValue)
    setReasonCode(reasons[0]?.code ?? '')
    setDetail('')
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
    <div className={open ? 'space-y-3' : 'inline-flex flex-wrap items-center gap-3'}>
      {open ? (
        <form className="space-y-4 rounded-lg border border-border bg-card p-4" onSubmit={onSubmit}>
          <p className="text-sm font-medium">Corregir {fieldLabel}</p>

          <div className="space-y-1">
            <label className="block text-sm" htmlFor={`value-${field}`}>
              Valor correcto
            </label>
            <Input
              id={`value-${field}`}
              type={numeric ? 'number' : 'text'}
              /*
                Whole pesos, because that is the only precision the screen can
                answer with: `formatPrice` writes prices without cents, and it is
                right to — the portal publishes them that way («$25.308» is twenty
                five thousand three hundred and eight, the dot separating
                thousands). Accepting `1234.50` here and printing 1235 back left
                the value stored correctly and unexplainable on screen, which is
                the one thing a correction may not be (RF-27).

                The column behind it is `Numeric(14, 4)`, and that is not an
                argument for cents: it is the money type the whole platform uses,
                for invoice totals and payments as much as for this. The day a
                price is shown with cents, this step follows the formatter — they
                are one decision, and it belongs to the screen.
              */
              step={numeric ? '1' : undefined}
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
              className={selectClassName}
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
            <Button
              variant="ghost"
              onClick={() => {
                setOpen(false)
                setMessage(null)
                discardDraft()
              }}
              type="button"
            >
              Cancelar
            </Button>
          </div>
        </form>
      ) : (
        // Abre el formulario que corrige: contorno, no azul de enlace (`RF-13`).
        <Button
          variant="outline"
          size="sm"
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
        </Button>
      )}
      <Outcome message={message} />
    </div>
  )
}
