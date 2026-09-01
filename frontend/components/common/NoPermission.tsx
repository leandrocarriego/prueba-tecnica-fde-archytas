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
export function NoPermission({ what }: { what?: string }) {
  return (
    <ErrorState
      title="No tenés permiso"
      action={
        <Button asChild variant="outline">
          <Link href="/tablero">Volver al tablero</Link>
        </Button>
      }
    >
      {what ? `Tu acceso no llega a ${what}.` : 'Tu acceso no llega a esta parte del sistema.'} Si
      creés que debería, pedíselo al dueño.
    </ErrorState>
  )
}
