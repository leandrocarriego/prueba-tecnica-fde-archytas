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
 * La forma es la misma tarjeta centrada que la pantalla de ingreso (`RF-05`):
 * quien abre este enlace no entró nunca a la plataforma, y esto es lo primero
 * que ve de ella.
 */
export default async function Page({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params
  const usable = await tokenIsUsable('invitacion', token)

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-10">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Definí tu clave</CardTitle>
          <CardDescription>
            {usable
              ? 'Este enlace es para que elijas la clave con la que vas a entrar. Nadie más la conoce.'
              : 'Esta invitación ya se usó o venció. Pedile al dueño que te mande una nueva.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {usable && (
            <PasswordForm
              action={async formData => {
                'use server'
                return setPasswordWithToken('invitacion', token, formData)
              }}
              label="Definir mi clave"
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
