'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { correctSupplier } from '@/app/actions/purchases'
import { Button } from '@/components/ui/button'
import { Input, selectClassName } from '@/components/ui/input'
import type { CorrectionReason } from '@/lib/operations/types'

interface SupplierCorrectionProps {
  supplierId: number
  /** `email`, `phone` o `payment_term_days`: los tres que el contrato admite. */
  field: 'email' | 'phone' | 'payment_term_days'
  fieldLabel: string
  currentValue: string
  reasons: CorrectionReason[]
}

/** Cómo salió el último intento, donde tenga que leerse. */
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
 * Corregir un dato de contacto del proveedor desde su ficha (RF-16 de 004).
 *
 * El criterio firmado dice «Marcela corrige el correo de un proveedor **desde su
 * ficha**», y hasta acá no había desde dónde: el `PATCH` existía, la server
 * action estaba escrita, y ningún componente la importaba. Un requisito no está
 * cumplido porque el backend lo acepte.
 *
 * Es el mismo diálogo que corrige un precio, con la misma forma y por la misma
 * razón: el motivo es obligatorio y sale de la API —es el backend el que rechaza
 * un `reason_code` desconocido, así que la lista que se ofrece y la que se
 * acepta son la misma—, y lo que el portal traiga después **no pisa** esto
 * (RF-19).
 *
 * Sólo tres campos, y no por omisión: la razón social y el CUIT son con lo que
 * se reconoce al proveedor, y `SupplierContactWrite` no los admite (RF-17). Acá
 * no hay una segunda copia de esa regla — no se pueden pedir porque el tipo de
 * `field` no los nombra.
 */
export function SupplierCorrection({
  supplierId,
  field,
  fieldLabel,
  currentValue,
  reasons,
}: SupplierCorrectionProps) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [value, setValue] = useState(currentValue)
  const [reasonCode, setReasonCode] = useState(reasons[0]?.code ?? '')
  const [detail, setDetail] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)

  /** Lo que se escribió y nunca se confirmó, descartado. */
  function discardDraft() {
    setValue(currentValue)
    setReasonCode(reasons[0]?.code ?? '')
    setDetail('')
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setMessage(null)

    // El plazo viaja como número y los otros dos como texto: el contrato pide
    // `payment_term_days: int | null`, y mandarle `"45"` sería pedirle a
    // Pydantic que adivine lo que esta pantalla ya sabe.
    const values =
      field === 'payment_term_days'
        ? { payment_term_days: Number(value) }
        : { [field]: value.trim() }

    const result = await correctSupplier(supplierId, values, reasonCode, detail || undefined)
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
    <div className={open ? 'space-y-2' : 'inline-flex flex-wrap items-center gap-2'}>
      {open ? (
        <form className="space-y-3 rounded-lg border bg-card p-3" onSubmit={onSubmit}>
          <p className="text-sm font-medium">Corregir {fieldLabel}</p>

          <div className="space-y-1">
            <label className="block text-sm" htmlFor={`supplier-value-${field}`}>
              Valor correcto
            </label>
            <Input
              id={`supplier-value-${field}`}
              type={field === 'payment_term_days' ? 'number' : 'text'}
              min={field === 'payment_term_days' ? 0 : undefined}
              step={field === 'payment_term_days' ? '1' : undefined}
              required
              value={value}
              onChange={event => setValue(event.target.value)}
            />
          </div>

          <div className="space-y-1">
            <label className="block text-sm" htmlFor={`supplier-reason-${field}`}>
              Por qué
            </label>
            <select
              className={selectClassName}
              id={`supplier-reason-${field}`}
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
            <label className="block text-sm" htmlFor={`supplier-detail-${field}`}>
              Aclaración (opcional)
            </label>
            <Input
              id={`supplier-detail-${field}`}
              maxLength={500}
              value={detail}
              onChange={event => setDetail(event.target.value)}
            />
          </div>

          <div className="flex gap-2">
            <Button disabled={saving} type="submit">
              Guardar
            </Button>
            <Button
              disabled={saving}
              type="button"
              variant="outline"
              onClick={() => {
                discardDraft()
                setOpen(false)
              }}
            >
              Cancelar
            </Button>
          </div>
        </form>
      ) : (
        <Button type="button" variant="outline" onClick={() => setOpen(true)}>
          Corregir
        </Button>
      )}
      <Outcome message={message} />
    </div>
  )
}
