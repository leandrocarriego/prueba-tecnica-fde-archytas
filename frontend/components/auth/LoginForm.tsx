'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { useFormStatus } from 'react-dom'

import { loginAction } from '@/app/actions/auth'
import { Button } from '@/components/ui/button'
import { Notice } from '@/components/ui/notice'
import { cn } from '@/lib/utils'
import { AuthField } from './AuthField'
import { useBranding } from './AuthBrandingProvider'

interface LoginFormProps {
  className?: string
}

/**
 * El botón de entrar.
 *
 * Es un componente hijo porque `useFormStatus` sólo informa el estado del
 * formulario adentro del cual se dibuja: leerlo desde el formulario mismo
 * devolvería `false` siempre.
 *
 * **Es el único naranja de la pantalla** (`RF-11`): entrar es la tarea. Antes
 * el color se pintaba a mano con `style` y dos manejadores de mouse que
 * reescribían el fondo al pasar por encima; eso es lo que `variant="brand"` ya
 * sabe hacer, con el token y con el foco visible que la guía pide.
 */
function SubmitButton({ label }: { label: string }) {
  const { pending } = useFormStatus()

  return (
    <Button type="submit" variant="brand" disabled={pending} className="w-full">
      {pending ? 'Ingresando…' : label}
    </Button>
  )
}

/**
 * La pantalla de ingreso (`docs/design/` 3m, `RF-05`).
 *
 * No trae tarjeta: la tarjeta es `AuthLayout`, que además pone el panel de
 * identidad al lado. Acá va sólo lo que la persona tiene que hacer —el título,
 * los dos campos y el botón— y, debajo, la salida para quien no se acuerda la
 * clave, que es un enlace porque lleva a otra pantalla y no ejecuta nada
 * (`UI-06`).
 *
 * Los textos siguen saliendo de `lib/branding.ts`.
 *
 * Usa `loginAction` directamente como `action` del formulario para que el
 * `redirect()` del servidor funcione.
 */
export function LoginForm({ className }: LoginFormProps) {
  const branding = useBranding()
  const searchParams = useSearchParams()
  // La acción del servidor vuelve con `?error=` cuando falla, así que la query
  // string es el único estado de error: no hay nada que guardar acá.
  const error = searchParams.get('error')

  return (
    <div className={cn('space-y-5', className)}>
      <h1 className="text-xl font-semibold">{branding.texts.loginTitle}</h1>

      <form action={loginAction} className="space-y-4">
        {error && <Notice tone="danger" title={error} />}
        <AuthField
          id="email"
          name="email"
          type="email"
          label={branding.texts.emailLabel}
          placeholder={branding.texts.emailPlaceholder}
          autoComplete="email"
          required
        />
        <AuthField
          id="password"
          name="password"
          type="password"
          label={branding.texts.passwordLabel}
          placeholder={branding.texts.passwordPlaceholder}
          autoComplete="current-password"
          required
        />
        <SubmitButton label={branding.texts.loginButton} />
      </form>

      <Link
        className="inline-block text-xs font-medium text-link hover:text-link-hover hover:underline"
        href="/reset-password"
      >
        {branding.texts.forgotPasswordLink}
      </Link>
    </div>
  )
}
