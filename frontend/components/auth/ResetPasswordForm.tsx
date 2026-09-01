'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'

import { requestRecovery, setPasswordWithToken } from '@/app/actions/access'
import { Button } from '@/components/ui/button'
import { Notice } from '@/components/ui/notice'
import { cn } from '@/lib/utils'
import { AuthField } from './AuthField'
import { useBranding } from './AuthBrandingProvider'

/** Lo que se dice cuando no se pudo ni siquiera preguntar. */
const UNREACHABLE = 'No pudimos contactar al servidor. Probá de nuevo en un momento.'

interface ResetPasswordFormProps {
  className?: string
  onSuccess?: () => void
}

/**
 * El encabezado de una de las dos caras.
 *
 * Es el mismo que el del ingreso —título y bajada, sin tarjeta— porque la
 * tarjeta y la marca las pone `AuthLayout`. Antes cada cara traía su `Card` con
 * el sello naranja repetido arriba, que es la marca dibujada dos veces en la
 * misma pantalla.
 */
function Heading({ title, description }: { title: string; description: string }) {
  return (
    <div className="space-y-1.5">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="text-[13px] leading-relaxed text-muted-foreground">{description}</p>
    </div>
  )
}

/**
 * El botón que guarda, en los dos pasos.
 *
 * Es **uno solo** y no dos a propósito: pedir el enlace y elegir la clave nueva
 * son dos caras de la misma pantalla, y el presupuesto de naranja de `RF-11` es
 * de la pantalla, no de la cara que esté visible.
 */
function SubmitButton({ label, loading }: { label: string; loading: boolean }) {
  return (
    <Button type="submit" variant="brand" className="w-full" disabled={loading}>
      {label}
    </Button>
  )
}

/**
 * Pedir el enlace de recuperación, y usarlo.
 *
 * Cuál de las dos caras se muestra lo decide el token de la URL, y no cambia
 * mientras el formulario está montado.
 *
 * **Las dos caras pasan por un Server Action, y ésa es la corrección.** Las dos
 * llamaban a la API con un `fetch` desde el navegador, contra
 * `NEXT_PUBLIC_API_URL` con `http://localhost:8000` de reserva. En una máquina
 * de desarrollo eso funciona y por eso nadie lo vio; en el servidor **el
 * backend no se publica** —sólo el frontend pasa por Traefik—, así que el
 * navegador pedía a su propia `localhost` y la pantalla contestaba «Failed to
 * fetch». Recuperar el acceso no funcionó nunca en producción.
 *
 * Los dos Server Actions que hacían falta ya existían en `app/actions/access.ts`
 * y no los llamaba nadie. El de pedir el enlace, además, **contesta lo mismo
 * exista o no la dirección**: la versión que había acá mostraba el detalle del
 * backend, lo que convertía este formulario en una forma de averiguar quién
 * tiene cuenta.
 *
 * La contracara honesta: sin fetch del navegador no hay forma de que esta
 * pantalla toque la API salvo a través del servidor de Next, que es la única
 * puerta que existe hacia afuera.
 */
export function ResetPasswordForm({ className, onSuccess }: ResetPasswordFormProps) {
  const branding = useBranding()
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token')

  const [email, setEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const step: 'request' | 'confirm' = token ? 'confirm' : 'request'

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const form = new FormData()
      form.set('email', email)
      // El Server Action contesta lo mismo exista o no la dirección, a
      // propósito: decirle a alguien que un correo no está registrado convierte
      // este formulario en una forma de averiguar quién tiene cuenta.
      const result = await requestRecovery(form)
      if (result.ok) setSuccess(true)
      else setError(result.message)
    } catch {
      // El Server Action llegó a tirar: el servidor de Next no pudo hablar con
      // la API. No hay detalle que dar que sirva de algo.
      setError(UNREACHABLE)
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (newPassword !== confirmPassword) {
      setError('Las contraseñas no coinciden')
      return
    }

    if (newPassword.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres')
      return
    }

    if (!token) {
      setError('Token no válido')
      return
    }

    setLoading(true)

    try {
      // El token viaja en la ruta y no en el cuerpo: identifica al enlace, y un
      // enlace es un recurso. La pantalla canónica de este paso es
      // `/recuperar/[token]`, que es adonde apunta el WhatsApp; esta rama queda
      // para quien llegue acá con `?token=`, y usa el **mismo** Server Action
      // que aquélla para que las dos no puedan divergir.
      const form = new FormData()
      form.set('new_password', newPassword)
      form.set('repeat_password', confirmPassword)
      const result = await setPasswordWithToken('recuperar', token, form)

      if (!result.ok) {
        setError(result.message)
        return
      }

      setSuccess(true)
      onSuccess?.()
      setTimeout(() => {
        router.push('/login')
      }, 2000)
    } catch {
      setError(UNREACHABLE)
    } finally {
      setLoading(false)
    }
  }

  if (step === 'request') {
    return (
      <div className={cn('space-y-5', className)}>
        <Heading
          title={branding.texts.resetPasswordTitle}
          description={branding.texts.resetPasswordSubtitle}
        />

        {success ? (
          <div className="space-y-4">
            <Notice tone="ok" title="Si ese email corresponde a un acceso, el enlace ya salió">
              Te llega por WhatsApp, al número registrado. Se usa una sola vez.
            </Notice>
            {/* Volver no es la tarea de esta pantalla: va en contorno. */}
            <Button variant="outline" className="w-full" onClick={() => router.push('/login')}>
              {branding.texts.backToLogin}
            </Button>
          </div>
        ) : (
          <>
            <form onSubmit={handleRequestReset} className="space-y-4">
              <AuthField
                id="email"
                type="email"
                label={branding.texts.emailLabel}
                placeholder={branding.texts.emailPlaceholder}
                value={email}
                onChange={e => setEmail(e.target.value)}
                autoComplete="email"
                required
                disabled={loading}
              />
              {error && <Notice tone="danger" title={error} />}
              <SubmitButton
                loading={loading}
                label={loading ? 'Enviando…' : branding.texts.resetPasswordButton}
              />
            </form>

            <Link
              className="inline-block text-xs font-medium text-link hover:text-link-hover hover:underline"
              href="/login"
            >
              {branding.texts.backToLogin}
            </Link>
          </>
        )}
      </div>
    )
  }

  return (
    <div className={cn('space-y-5', className)}>
      <Heading title="Nueva contraseña" description="Elegí la clave con la que vas a entrar." />

      {success ? (
        <Notice tone="ok" title="Contraseña restablecida">
          Te llevamos a la pantalla de ingreso.
        </Notice>
      ) : (
        <form onSubmit={handleConfirmReset} className="space-y-4">
          <AuthField
            id="newPassword"
            type="password"
            label={branding.texts.passwordLabel}
            placeholder={branding.texts.passwordPlaceholder}
            value={newPassword}
            onChange={e => setNewPassword(e.target.value)}
            autoComplete="new-password"
            required
            disabled={loading}
            minLength={8}
          />
          <AuthField
            id="confirmPassword"
            type="password"
            label={branding.texts.confirmPasswordLabel}
            placeholder={branding.texts.passwordPlaceholder}
            value={confirmPassword}
            onChange={e => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            required
            disabled={loading}
            minLength={8}
          />
          {error && <Notice tone="danger" title={error} />}
          <SubmitButton
            loading={loading}
            label={loading ? 'Restableciendo…' : 'Restablecer contraseña'}
          />
        </form>
      )}
    </div>
  )
}
