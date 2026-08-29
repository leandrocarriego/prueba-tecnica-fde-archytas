'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { savePriceUpdateSettings } from '@/app/actions/prices'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { PriceUpdateSettings } from '@/lib/catalog/types'

interface SettingsFormProps {
  settings: PriceUpdateSettings
}

/**
 * The two parameters of the feature (RF-18, RF-19).
 *
 * A Client Component because it is a form with state. The bounds mirror the
 * ones the backend enforces: the browser is where a mistake is caught early,
 * never where it is decided.
 */
export function SettingsForm({ settings }: SettingsFormProps) {
  const router = useRouter()
  const [interval, setInterval] = useState(String(settings.interval_hours))
  const [threshold, setThreshold] = useState(String(settings.highlight_threshold_pct))
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setMessage(null)

    const result = await savePriceUpdateSettings(Number(interval), Number(threshold))
    setMessage(
      result.ok
        ? { ok: true, text: 'Guardado. La frecuencia nueva rige desde la consulta siguiente.' }
        : { ok: false, text: result.message }
    )
    setSaving(false)
    if (result.ok) router.refresh()
  }

  return (
    <form className="max-w-md space-y-6" onSubmit={onSubmit}>
      <div className="space-y-2">
        <label className="block text-sm font-medium" htmlFor="interval">
          Cada cuántas horas se consulta el portal
        </label>
        <Input
          id="interval"
          type="number"
          min={1}
          max={168}
          required
          value={interval}
          onChange={event => setInterval(event.target.value)}
        />
        <p className="text-sm text-muted-foreground">
          El proveedor publica precios nuevos dos veces por día: consultar más seguido no trae
          precios nuevos.
        </p>
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium" htmlFor="threshold">
          Porcentaje de suba a partir del cual un producto se destaca
        </label>
        <Input
          id="threshold"
          type="number"
          min={0}
          max={1000}
          step="0.1"
          required
          value={threshold}
          onChange={event => setThreshold(event.target.value)}
        />
        <p className="text-sm text-muted-foreground">
          Se compara contra el precio que el producto tenía en la actualización anterior.
        </p>
      </div>

      <div className="flex items-center gap-4">
        <Button type="submit" disabled={saving}>
          {saving ? 'Guardando…' : 'Guardar'}
        </Button>
        {message && (
          <p className={`text-sm ${message.ok ? 'text-emerald-700' : 'text-red-700'}`}>
            {message.text}
          </p>
        )}
      </div>
    </form>
  )
}
