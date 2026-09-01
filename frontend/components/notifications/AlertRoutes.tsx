'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { setAlertRoute } from '@/app/actions/alerts'
import { ALERT_KINDS, ALERT_ROLES, type AlertRoute } from '@/lib/notifications/types'
import { Card } from '@/components/ui/card'
import { selectClassName } from '@/components/ui/input'

/**
 * Quién recibe cada tipo de aviso (RF-37 de 007).
 *
 * La ruta existía desde el primer día y **ninguna pantalla la llamaba**: el
 * dueño sólo podía cambiar los destinatarios con una request a mano, que es
 * tanto como no poder. Vive acá, en la misma pantalla que los parámetros del
 * sistema, porque es la misma clase de decisión: un valor que el dueño elige y
 * que rige para todo el equipo.
 *
 * Client Component por lo mismo que `ParameterCard`: es un control con estado, y
 * cada fila se guarda sola para que un rechazo diga cuál falló.
 *
 * **Cuántas personas alcanza cada ruta se muestra al lado**, y no es decoración:
 * una ruta apuntada a un rol que nadie ocupa entrega el aviso al dueño por
 * descarte, y el dueño tiene que enterarse antes de que el aviso no llegue.
 */
export function AlertRoutes({ routes }: { routes: AlertRoute[] }) {
  const router = useRouter()
  const [saving, setSaving] = useState<string | null>(null)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)

  async function choose(route: AlertRoute, role: string) {
    setSaving(route.kind)
    setMessage(null)
    const result = await setAlertRoute(route.kind, role)
    setSaving(null)
    setMessage(result.ok ? { ok: true, text: 'Guardado.' } : { ok: false, text: result.message })
    if (result.ok) router.refresh()
  }

  return (
    <section className="space-y-3">
      <Card className="overflow-hidden">
        <header className="space-y-1 p-5">
          <h2 className="font-semibold">Por dónde llegan los avisos</h2>
          <p className="text-sm text-muted-foreground">
            El aviso llega por WhatsApp al número registrado de cada persona que tenga el rol
            elegido. Ventas no figura: no accede a la bandeja de mensajes de la que hablan estos
            avisos.
          </p>
        </header>

        {routes.map(route => (
          <div
            key={route.kind}
            className="flex flex-wrap items-center justify-between gap-3 border-t border-border p-4"
          >
            <div>
              <p className="font-medium">{ALERT_KINDS[route.kind] ?? route.kind}</p>
              <p className="text-sm text-muted-foreground">
                {route.recipients === 0
                  ? 'Hoy no lo recibe nadie: nadie ocupa ese rol, así que el aviso le llega al dueño.'
                  : route.recipients === 1
                    ? 'Hoy lo recibe 1 persona.'
                    : `Hoy lo reciben ${route.recipients} personas.`}
              </p>
            </div>

            <label className="flex items-center gap-2 text-sm">
              <span className="sr-only">Quién recibe {ALERT_KINDS[route.kind] ?? route.kind}</span>
              <select
                className={selectClassName}
                disabled={saving === route.kind}
                value={route.role}
                onChange={event => choose(route, event.target.value)}
              >
                {Object.entries(ALERT_ROLES).map(([role, name]) => (
                  <option key={role} value={role}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        ))}
      </Card>

      <p aria-live="polite" className={`text-sm ${message?.ok === false ? 'text-danger' : ''}`}>
        {message?.text ?? ''}
      </p>
    </section>
  )
}
