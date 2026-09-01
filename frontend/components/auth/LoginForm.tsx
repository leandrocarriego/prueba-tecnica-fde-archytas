'use client'

import { useSearchParams } from 'next/navigation'
import { useFormStatus } from 'react-dom'

import { loginAction } from '@/app/actions/auth'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Notice } from '@/components/ui/notice'
import { cn } from '@/lib/utils'
import { useBranding } from './AuthBrandingProvider'

interface LoginFormProps {
  className?: string
  renderLogo?: (config: ReturnType<typeof useBranding>) => React.ReactNode
  renderFooter?: (config: ReturnType<typeof useBranding>) => React.ReactNode
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
      {pending ? 'Iniciando sesión…' : label}
    </Button>
  )
}

/**
 * La pantalla de ingreso.
 *
 * Los textos siguen saliendo de `lib/branding.ts`; lo que ya no sale de ahí es
 * el aspecto: la tarjeta, los radios y el color son los mismos que los del
 * resto de la plataforma, porque es la misma plataforma (`RF-05`).
 *
 * Usa `loginAction` directamente como `action` del formulario para que el
 * `redirect()` del servidor funcione.
 */
export function LoginForm({ className, renderLogo, renderFooter }: LoginFormProps) {
  const branding = useBranding()
  const searchParams = useSearchParams()
  // La acción del servidor vuelve con `?error=` cuando falla, así que la query
  // string es el único estado de error: no hay nada que guardar acá.
  const error = searchParams.get('error')
  const alignment = branding.formOptions?.textAlignment === 'left' ? 'text-left' : 'text-center'

  return (
    <Card className={className}>
      <CardHeader className="space-y-1">
        {renderLogo && renderLogo(branding)}
        <CardTitle className={cn('text-2xl', alignment)}>{branding.texts.loginTitle}</CardTitle>
        <CardDescription className={alignment}>{branding.texts.loginSubtitle}</CardDescription>
      </CardHeader>
      <CardContent>
        <form action={loginAction} className="space-y-5">
          {error && <Notice tone="danger" title={error} />}
          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium">
              {branding.texts.emailLabel}
            </label>
            <Input
              id="email"
              name="email"
              type="email"
              placeholder={branding.texts.emailPlaceholder}
              required
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">
              {branding.texts.passwordLabel}
            </label>
            <Input
              id="password"
              name="password"
              type="password"
              placeholder={branding.texts.passwordPlaceholder}
              required
            />
          </div>
          <SubmitButton label={branding.texts.loginButton} />
          {renderFooter && renderFooter(branding)}
        </form>
      </CardContent>
    </Card>
  )
}
