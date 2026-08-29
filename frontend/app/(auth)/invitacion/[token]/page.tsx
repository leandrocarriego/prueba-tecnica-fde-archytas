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
  const sirve = await tokenIsUsable('invitacion', token)

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-10">
      <h1 className="mb-2 text-2xl font-semibold">Definí tu clave</h1>

      {sirve ? (
        <>
          <p className="mb-6 text-muted-foreground">
            Este enlace es para que elijas la clave con la que vas a entrar. Nadie más la conoce.
          </p>
          <PasswordForm
            action={async formData => {
              'use server'
              return setPasswordWithToken('invitacion', token, formData)
            }}
            etiqueta="Definir mi clave"
          />
          <Link href="/login" className="mt-6 text-center text-sm underline underline-offset-4">
            Ir a la pantalla de ingreso
          </Link>
        </>
      ) : (
        <>
          <p className="mb-6 text-muted-foreground">
            Esta invitación ya se usó o venció. Pedile al dueño que te mande una nueva.
          </p>
          <Link href="/login" className="text-center text-sm underline underline-offset-4">
            Ir a la pantalla de ingreso
          </Link>
        </>
      )}
    </main>
  )
}
