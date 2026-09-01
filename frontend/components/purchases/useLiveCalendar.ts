'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'

import { announceCalendarPresence, leaveCalendarPresence } from '@/app/actions/purchases'

/** Qué está pasando con el canal, en los términos en que la pantalla lo dice. */
export type LiveState = 'conectando' | 'en-vivo' | 'caido'

/** El último cambio que llegó de otra persona, para poder decir quién lo hizo. */
export interface LiveChange {
  action: string
  actorName: string
  at: number
}

/** Alguien que tiene esta pantalla abierta ahora mismo. */
export interface Viewer {
  id: number
  name: string
  at: number
}

/** Cada cuánto se anuncia que uno está mirando. */
const PRESENCE_MS = 20_000

/**
 * Cuánto vale un anuncio antes de darlo por vencido.
 *
 * Tres veces el intervalo y no dos: con dos, un anuncio que se pierde —el canal
 * es «lo entrega a quien esté escuchando», no garantiza nada— hace desaparecer
 * de las otras pantallas a alguien que sigue ahí. Con tres hacen falta dos
 * pérdidas seguidas, y el costo de equivocarse para el otro lado es que alguien
 * que se fue tarde un minuto en desaparecer.
 */
const PRESENCE_TTL_MS = PRESENCE_MS * 3 + 5_000

/**
 * El calendario, mirado por varias personas a la vez (H5 de 006).
 *
 * Dos cosas por el mismo canal, y son distintas: **qué cambió** —que obliga a
 * releer la pantalla— y **quién está mirando**, que no cambia ningún dato y sin
 * embargo cambia cómo se trabaja: mover un vencimiento sabiendo que hay alguien
 * más con la pantalla abierta no es lo mismo que moverlo a ciegas.
 *
 * Con cada cambio vuelve a pedir la pantalla al servidor en lugar de parchear lo
 * que ya tiene dibujado. Es deliberado: la verdad está en la base a una consulta
 * de distancia, y un cliente que aplica cambios por su cuenta termina mostrando
 * un estado que no existe en ningún lado — sobre todo después de una
 * desconexión, donde le faltarían justo los mensajes que no recibió. Al
 * reconectar se relee todo, que es RF-36.
 *
 * **La presencia no vive en el servidor.** Cada navegador anuncia que está, cada
 * {@link PRESENCE_MS} ms, y los demás lo escuchan y lo olvidan solos si deja de
 * anunciarse. Una lista de conectados guardada del otro lado habría que
 * limpiarla cuando alguien cierra el navegador de golpe, que es exactamente el
 * caso en que nadie avisa.
 *
 * El aviso de caída es el evento `error` de `EventSource`, no un temporizador
 * adivinando: RF-35 pide avisar cuando la conexión se corta, y el navegador ya
 * sabe cuándo pasó.
 */
export function useLiveCalendar({
  announce = true,
}: {
  /**
   * Si esta pantalla se anuncia, además de escuchar.
   *
   * Anunciarse pide `CALENDAR:WRITE` —la regla es que un `POST` exige el nivel
   * que cambia, y la verifica un test que rompe el build—, así que quien tiene
   * el calendario en sólo lectura recibiría un 403 cada veinte segundos. Ve
   * quiénes están y no aparece en la lista de los demás, que es lo correcto:
   * la presencia existe para que dos personas no se pisen editando lo mismo, y
   * quien no puede editar no pisa a nadie.
   */
  announce?: boolean
} = {}): {
  state: LiveState
  lastChange: LiveChange | null
  viewers: Viewer[]
} {
  const router = useRouter()
  const [state, setState] = useState<LiveState>('conectando')
  const [lastChange, setLastChange] = useState<LiveChange | null>(null)
  const [viewers, setViewers] = useState<Viewer[]>([])

  // El refresh se pide por referencia para no volver a abrir el canal cada vez
  // que el router cambia de identidad: reconectar en cada cambio recibido sería
  // perder mensajes justo cuando más llegan.
  const refresh = useRef(router.refresh)
  useEffect(() => {
    refresh.current = router.refresh
  }, [router])

  const remember = useCallback((id: number, name: string) => {
    setViewers(current => {
      const rest = current.filter(one => one.id !== id)
      return [...rest, { id, name, at: Date.now() }]
    })
  }, [])

  /** Sacar a alguien en el acto, porque avisó que se iba. */
  const forget = useCallback((id: number) => {
    setViewers(current => current.filter(one => one.id !== id))
  }, [])

  useEffect(() => {
    const source = new EventSource('/api/calendar/stream')

    source.onopen = () => setState('en-vivo')

    source.onmessage = event => {
      setState('en-vivo')
      try {
        const message = JSON.parse(event.data) as {
          topic?: string
          data?: {
            action?: string
            actor_name?: string
            user_id?: number
            name?: string
            leaving?: boolean
          }
        }

        if (message.topic === 'presence') {
          const id = message.data?.user_id
          if (typeof id !== 'number') return
          // Un aviso de despedida saca a la persona en el acto; sin él habría
          // que esperar a que se le venza el turno, y hasta entonces la
          // pantalla diría que hay alguien mirando que ya se fue.
          if (message.data?.leaving) forget(id)
          else remember(id, message.data?.name ?? '')
          return
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
  }, [remember, forget])

  // Anunciarse: una vez al abrir —para que los que ya están se enteren en el
  // acto— y después cada tanto. Quien sólo mira no se anuncia.
  useEffect(() => {
    if (!announce) return
    void announceCalendarPresence()
    const timer = setInterval(() => void announceCalendarPresence(), PRESENCE_MS)

    /*
      Y despedirse, que es la mitad que faltaba. `sendBeacon` es lo único que un
      navegador entrega mientras la pestaña se está cerrando —un `fetch` normal
      se cancela con la página—, y va contra el proxy porque es la única puerta
      del navegador hacia la API: la sesión vive en una cookie que el JavaScript
      no lee, y el proxy es quien la convierte en cabecera.

      `pagehide` y no `beforeunload`: es el evento que también dispara cuando el
      navegador se lleva la página a su caché, y es el que Safari en un teléfono
      efectivamente emite.
    */
    const goodbye = () => navigator.sendBeacon?.('/api/proxy/calendar/presence/leaving')
    window.addEventListener('pagehide', goodbye)

    return () => {
      clearInterval(timer)
      window.removeEventListener('pagehide', goodbye)
      // Salir del calendario sin cerrar la pestaña —que es lo que pasa la mayor
      // parte de las veces— no dispara `pagehide`, así que se avisa acá.
      void leaveCalendarPresence()
    }
  }, [announce])

  // Olvidar a los que dejaron de anunciarse. Se revisa con el mismo pulso que
  // se anuncia, que es suficiente: nadie mira una lista de presencias
  // esperando el segundo exacto en que alguien desaparece.
  useEffect(() => {
    const timer = setInterval(() => {
      const alive = Date.now() - PRESENCE_TTL_MS
      setViewers(current => {
        const kept = current.filter(one => one.at >= alive)
        return kept.length === current.length ? current : kept
      })
    }, PRESENCE_MS)
    return () => clearInterval(timer)
  }, [])

  return { state, lastChange, viewers }
}
