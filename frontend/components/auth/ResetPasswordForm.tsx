'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'

import { Button } from '@/components/ui/button'
import { Notice } from '@/components/ui/notice'
import { cn } from '@/lib/utils'
import { AuthField } from './AuthField'
import { useBranding } from './AuthBrandingProvider'

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
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/auth/password-reset/request`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email }),
        }
      )

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Error al solicitar reseteo')
      }

      setSuccess(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al solicitar reseteo')
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
      // The token travels in the path now, not in the body: it identifies the
      // link, and a link is a resource. The canonical screen for this step is
      // /recuperar/[token], which is where the WhatsApp message points; this
      // branch stays for anybody who arrives here with ?token=.
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/auth/password-reset/${encodeURIComponent(token)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ new_password: newPassword }),
        }
      )

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Error al restablecer contraseña')
      }

      setSuccess(true)
      onSuccess?.()
      setTimeout(() => {
        router.push('/login')
      }, 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al restablecer contraseña')
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
