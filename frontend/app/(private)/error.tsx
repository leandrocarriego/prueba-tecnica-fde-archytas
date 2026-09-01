'use client'

import { Button } from '@/components/ui/button'
import { ErrorState } from '@/components/ui/state'

/**
 * Lo que se ve cuando una pantalla del área privada se rompe de verdad.
 *
 * Un error de render no lo puede resolver quien mira, así que la pantalla no le
 * pide nada: le dice qué pasó y le ofrece reintentar. `reset()` vuelve a montar
 * el segmento sin recargar toda la aplicación, que es lo que hace que un fallo
 * pasajero —el backend que tardó de más— se arregle apretando una vez.
 *
 * El botón va en contorno y no en naranja: reintentar no es la tarea principal
 * de ninguna pantalla (`RF-11`).
 */
export default function PrivateError({ reset }: { error: Error; reset: () => void }) {
  return (
    <ErrorState
      title="No pudimos mostrar esta pantalla"
      action={
        <Button variant="outline" onClick={reset}>
          Reintentar
        </Button>
      }
    >
      Se cortó algo mientras la armábamos. Probá de nuevo; si sigue pasando, avisá.
    </ErrorState>
  )
}
