'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'

/** Qué está pasando con el canal, en los términos en que la pantalla lo dice. */
export type LiveState = 'conectando' | 'en-vivo' | 'caido'

/** El último cambio que llegó de otra persona, para poder decir quién lo hizo. */
export interface LiveChange {
  action: string
  actorName: string
  at: number
}

/**
 * El calendario, mirado por dos personas a la vez (H5 de 006).
 *
 * Escucha el canal y, con cada cambio, vuelve a pedir la pantalla al servidor
 * en lugar de intentar parchear lo que ya tiene dibujado. Es deliberado: la
 * verdad está en la base a una consulta de distancia, y un cliente que aplica
 * cambios por su cuenta termina mostrando un estado que no existe en ningún
 * lado — sobre todo después de una desconexión, donde le faltarían justo los
 * mensajes que no recibió. Al reconectar se relee todo, que es RF-36.
 *
 * El aviso de caída es el evento `error` de `EventSource`, no un temporizador
 * adivinando: RF-35 pide avisar cuando la conexión se corta, y el navegador ya
 * sabe cuándo pasó.
 */
export function useLiveCalendar(): { state: LiveState; lastChange: LiveChange | null } {
  const router = useRouter()
  const [state, setState] = useState<LiveState>('conectando')
  const [lastChange, setLastChange] = useState<LiveChange | null>(null)
  // El refresh se pide por referencia para no volver a abrir el canal cada vez
  // que el router cambia de identidad: reconectar en cada cambio recibido sería
  // perder mensajes justo cuando más llegan.
  const refresh = useRef(router.refresh)
  useEffect(() => {
    refresh.current = router.refresh
  }, [router])

  useEffect(() => {
    const source = new EventSource('/api/calendar/stream')

    source.onopen = () => setState('en-vivo')

    source.onmessage = event => {
      setState('en-vivo')
      try {
        const message = JSON.parse(event.data) as {
          topic?: string
          data?: { action?: string; actor_name?: string }
        }
        if (message.topic !== 'calendar') return
        setLastChange({
          action: message.data?.action ?? 'cambió',
          actorName: message.data?.actor_name ?? '',
          at: Date.now(),
        })
        refresh.current()
      } catch {
        // Un mensaje que no se entiende no rompe la pantalla: se pide de nuevo
        // el calendario, que es lo que se iba a hacer igual.
        refresh.current()
      }
    }

    // `EventSource` reintenta solo; lo único que hace falta acá es decirlo.
    source.onerror = () => setState('caido')

    return () => source.close()
  }, [])

  return { state, lastChange }
}
