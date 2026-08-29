import Link from 'next/link'

import { SettingsForm } from '@/components/catalog/SettingsForm'
import { fetchFromApi } from '@/lib/api/server'
import type { PriceUpdateSettings } from '@/lib/catalog/types'

export const metadata = {
  title: 'Configuración de precios — Plataforma Cordillera',
}

/**
 * The owner's screen for the two parameters of this feature (H4).
 *
 * The gate is the endpoint, not this page: `GET /price-updates/settings` is
 * owner-only, so anybody else lands on the message below instead of a form
 * that would fail on save. Hiding a link is not authorisation.
 */
export default async function PriceSettingsPage() {
  const settings = await fetchFromApi<PriceUpdateSettings>('/price-updates/settings')

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-8">
      <Link className="text-sm text-muted-foreground underline" href="/precios">
        « Volver a la lista de precios
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Configuración de la actualización</h1>
        <p className="text-sm text-muted-foreground">
          Estos valores los decide el dueño, y rigen para todo el equipo.
        </p>
      </header>

      {settings === null ? (
        <p className="rounded border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          Esta pantalla es del dueño. Si necesitás cambiar la frecuencia o el porcentaje, pedíselo.
        </p>
      ) : (
        <SettingsForm settings={settings} />
      )}
    </main>
  )
}
