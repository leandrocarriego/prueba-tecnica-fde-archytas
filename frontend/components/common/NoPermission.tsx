import Link from 'next/link'

import { Button } from '@/components/ui/button'
import { ErrorState } from '@/components/ui/state'

/**
 * What somebody sees when they reach for a section that is not theirs.
 *
 * Deliberately not a redirect to the login: *no entraste* and *no te toca* are
 * different things, and sending the second one to a login form tells a person
 * their session broke when it did not. The refusal is also recorded, so the
 * owner sees it — this screen is only the half the person reads.
 *
 * Tiene la forma de `<ErrorState>` y no una propia: la usan trece pantallas, y
 * cuando el error de permiso se dibuja distinto del resto de los errores, quien
 * lo ve tiene que leerlo entero para entender de cuál de los dos se trata
 * (`RF-19`).
 */
/**
 * `a` + `el` es `al`, y en castellano no es opcional.
 *
 * Las trece pantallas pasan el nombre de su sección con artículo —«el tablero
 * del negocio», «las ventas»—, así que la preposición se contrae acá, una vez,
 * en lugar de pedirle a cada llamador que la escriba ya contraída: eso sería
 * pedirle a trece lugares que se acuerden de una regla de gramática.
 */
function reaching(what: string): string {
  return what.startsWith('el ') ? `al ${what.slice(3)}` : `a ${what}`
}

/**
 * `isHome` existe porque el tablero también se puede negar.
 *
 * Ofrecerle «Volver al tablero» a quien acaba de rebotar contra el tablero
 * —que es lo que le pasa a compras apenas entra— es un lazo: el único botón de
 * la pantalla lleva a la pantalla que lo echó. Cuando la sección negada es el
 * propio tablero, la negativa se queda sin acción antes que con una que no
 * lleva a ninguna parte.
 */
export function NoPermission({ what, isHome = false }: { what?: string; isHome?: boolean }) {
  return (
    <ErrorState
      title="No tenés permiso"
      action={
        isHome ? undefined : (
          <Button asChild variant="outline">
            <Link href="/tablero">Volver al tablero</Link>
          </Button>
        )
      }
    >
      {what
        ? `Tu acceso no llega ${reaching(what)}.`
        : 'Tu acceso no llega a esta parte del sistema.'}{' '}
      Si creés que debería, pedíselo al dueño.
    </ErrorState>
  )
}
