'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { setAlertRoute, testAlertRoute } from '@/app/actions/alerts'
import { ALERT_KINDS, ALERT_ROLES, type AlertRoute } from '@/lib/notifications/types'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { selectClassName } from '@/components/ui/input'
import { Notice } from '@/components/ui/notice'

/**
 * Quién recibe cada tipo de aviso (RF-37 de 007).
 *
 * La ruta existía desde el primer día y **ninguna pantalla la llamaba**: el
 * dueño sólo podía cambiar los destinatarios con una request a mano, que es
 * tanto como no poder. Vive en «Configuración», junto a los parámetros y a los
 * accesos, porque es la misma clase de decisión: algo que el dueño elige una vez
 * y rige para todo el equipo. Qué son estos avisos y por dónde llegan lo dice la
 * pantalla; acá está el control.
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
  const [testing, setTesting] = useState<string | null>(null)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)
  // El resultado de la última prueba, aparte del renglón de «Guardado.»: es un
  // hecho más largo —a cuántos teléfonos salió y qué mirar ahora— y dura hasta
  // que se prueba otra cosa.
  const [tested, setTested] = useState<{ ok: boolean; title: string; detail: string } | null>(null)

  async function choose(route: AlertRoute, role: string) {
    setSaving(route.kind)
    setMessage(null)
    const result = await setAlertRoute(route.kind, role)
    setSaving(null)
    setMessage(result.ok ? { ok: true, text: 'Guardado.' } : { ok: false, text: result.message })
    if (result.ok) router.refresh()
  }

  /**
   * Mandar el aviso de prueba de un tipo.
   *
   * La respuesta dice a qué teléfonos salió, no que hayan llegado: entregarlo
   * es trabajo del worker contra WhatsApp, y esperarlo acá dejaría la pantalla
   * colgada de un servicio de un tercero. Así que el aviso de abajo dice
   * exactamente eso — salió, mirá el teléfono— en vez de afirmar una entrega
   * que nadie confirmó.
   */
  async function probar(route: AlertRoute) {
    setTesting(route.kind)
    setMessage(null)
    setTested(null)
    const result = await testAlertRoute(route.kind)
    setTesting(null)
    if (!result.ok) {
      setTested({ ok: false, title: 'No se pudo mandar la prueba', detail: result.message })
      return
    }
    const phones = result.data.sent_to
    setTested({
      ok: true,
      title:
        phones.length === 1
          ? `Salió al teléfono ${phones[0]}`
          : `Salió a ${phones.length} teléfonos: ${phones.join(', ')}`,
      detail:
        'Llega como WhatsApp, identificado como prueba en la primera línea. Si no aparece en un ' +
        'minuto, el problema está en la sesión de WhatsApp y no en esta configuración.',
    })
  }

  return (
    <section className="space-y-3">
      <Card className="overflow-hidden">
        {routes.map((route, index) => (
          <div
            key={route.kind}
            className={`flex flex-wrap items-center justify-between gap-3 p-4 ${index > 0 ? 'border-t border-border' : ''}`}
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

            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 text-sm">
                <span className="sr-only">
                  Quién recibe {ALERT_KINDS[route.kind] ?? route.kind}
                </span>
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

              {/*
                Probar es una acción, no una decisión: va en contorno. El naranja
                de esta pantalla no se gasta acá — configurar a quién le llega
                cada aviso es lo que se viene a hacer, y probarlo es cómo se
                comprueba que quedó bien.
              */}
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={testing !== null || saving === route.kind}
                onClick={() => probar(route)}
              >
                {testing === route.kind ? 'Mandando…' : 'Probar el envío'}
              </Button>
            </div>
          </div>
        ))}
      </Card>

      {/*
        El resultado de la prueba, con su propia forma: no es «guardado», es un
        hecho sobre el mundo de afuera —salió un WhatsApp a un teléfono— y el
        que lo pidió tiene que saber adónde mirar para comprobarlo.
      */}
      {tested && (
        <Notice tone={tested.ok ? 'info' : 'danger'} title={tested.title}>
          {tested.detail}
        </Notice>
      )}

      <p aria-live="polite" className={`text-sm ${message?.ok === false ? 'text-danger' : ''}`}>
        {message?.text ?? ''}
      </p>
    </section>
  )
}
