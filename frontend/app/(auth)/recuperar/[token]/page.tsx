import Link from 'next/link'

import { setPasswordWithToken, tokenIsUsable } from '@/app/actions/access'
import { PasswordForm } from '@/components/auth/PasswordForm'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

/**
 * Public on purpose: whoever holds this link holds the credential, and by
 * definition has no session yet. The link works once and it expires — both are
 * checked on the server, and this screen only asks first so nobody types a
 * password into a form that was never going to work.
 *
 * Misma tarjeta que la invitación y que el ingreso (`RF-05`).
 */
export default async function Page({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params
  const usable = await tokenIsUsable('recuperar', token)

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-10">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Poné una clave nueva</CardTitle>
          <CardDescription>
            {usable
              ? 'Elegí la clave con la que vas a entrar de ahora en más.'
              : 'Este enlace ya se usó o venció. Pedí la recuperación otra vez desde la pantalla de ingreso.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {usable && (
            <PasswordForm
              action={async formData => {
                'use server'
                return setPasswordWithToken('recuperar', token, formData)
              }}
              label="Guardar la clave"
              singleUse
            />
          )}
          {/* Ir al ingreso no es la tarea de esta pantalla: va en contorno. */}
          <Button asChild variant="outline" className="w-full">
            <Link href="/login">Ir a la pantalla de ingreso</Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  )
}
