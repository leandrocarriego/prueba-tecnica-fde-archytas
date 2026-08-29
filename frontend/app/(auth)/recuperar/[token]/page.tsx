import Link from 'next/link'

import { setPasswordWithToken, tokenIsUsable } from '@/app/actions/access'
import { PasswordForm } from '@/components/auth/PasswordForm'

/**
 * Public on purpose: whoever holds this link holds the credential, and by
 * definition has no session yet. The link works once and it expires — both are
 * checked on the server, and this screen only asks first so nobody types a
 * password into a form that was never going to work.
 */
export default async function Page({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params
  const usable = await tokenIsUsable('recuperar', token)

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-10">
      <h1 className="mb-2 text-2xl font-semibold">Poné una clave nueva</h1>

      {usable ? (
        <>
          <p className="mb-6 text-muted-foreground">
            Elegí la clave con la que vas a entrar de ahora en más.
          </p>
          <PasswordForm
            action={async formData => {
              'use server'
              return setPasswordWithToken('recuperar', token, formData)
            }}
            label="Guardar la clave"
            singleUse
          />
          <Link href="/login" className="mt-6 rounded bg-gray-900 px-4 py-2 text-center text-white">
            Ir a la pantalla de ingreso
          </Link>
        </>
      ) : (
        <>
          <p className="mb-6 text-muted-foreground">
            Este enlace ya se usó o venció. Pedí la recuperación otra vez desde la pantalla de
            ingreso.
          </p>
          <Link href="/login" className="text-center text-sm underline underline-offset-4">
            Ir a la pantalla de ingreso
          </Link>
        </>
      )}
    </main>
  )
}
