'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Notice } from '@/components/ui/notice'
import { useBranding } from './AuthBrandingProvider'

interface ResetPasswordFormProps {
  className?: string
  onSuccess?: () => void
  renderLogo?: (config: ReturnType<typeof useBranding>) => React.ReactNode
}

/**
 * La marca, arriba de la tarjeta.
 *
 * Estaba escrita tres veces en este archivo, con la misma escalera de tamaños
 * copiada en cada una: acá es una sola, y el cuadrado naranja sale del token
 * como el resto de la aplicación (`RF-05`).
 */
function BrandMark({ branding }: { branding: ReturnType<typeof useBranding> }) {
  const { logo } = branding
  const size = logo.size === 'sm' ? 'size-8' : logo.size === 'lg' ? 'size-16' : 'size-12'
  const Logo = logo.component

  if (!Logo && !logo.src && !logo.text) return null

  return (
    <div className="mb-4 flex items-center justify-center">
      {Logo ? (
        <Logo className={size} />
      ) : logo.src ? (
        /*
         * El logo lo configura `lib/branding.ts` y puede ser cualquier URL,
         * incluida una que `next/image` no puede optimizar sin declarar antes
         * su dominio en la config. Hoy no hay ninguna: la marca es el texto.
         */
        // eslint-disable-next-line @next/next/no-img-element
        <img src={logo.src} alt={logo.alt || 'Logo'} className={size} />
      ) : (
        <div
          className={`${size} flex items-center justify-center rounded-lg bg-brand text-2xl font-bold text-brand-foreground`}
        >
          {logo.text}
        </div>
      )}
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
export function ResetPasswordForm({ className, onSuccess, renderLogo }: ResetPasswordFormProps) {
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
      <Card className={className}>
        <CardHeader className="space-y-1">
          {renderLogo ? renderLogo(branding) : <BrandMark branding={branding} />}
          <CardTitle className="text-center text-2xl">
            {branding.texts.resetPasswordTitle}
          </CardTitle>
          <CardDescription className="text-center">
            {branding.texts.resetPasswordSubtitle}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {success ? (
            <div className="space-y-4">
              <Notice
                tone="ok"
                title="Si el email existe, se envió un enlace de restablecimiento"
              />
              {/* Volver no es la tarea de esta pantalla: va en contorno. */}
              <Button variant="outline" className="w-full" onClick={() => router.push('/login')}>
                {branding.texts.backToLogin}
              </Button>
            </div>
          ) : (
            <form onSubmit={handleRequestReset} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium">
                  {branding.texts.emailLabel}
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder={branding.texts.emailPlaceholder}
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  disabled={loading}
                />
              </div>
              {error && <Notice tone="danger" title={error} />}
              <SubmitButton
                loading={loading}
                label={loading ? 'Enviando…' : branding.texts.resetPasswordButton}
              />
              <div className="text-center">
                <Button asChild variant="link" size="sm">
                  <Link href="/login">{branding.texts.backToLogin}</Link>
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader className="space-y-1">
        <BrandMark branding={branding} />
        <CardTitle className="text-center text-2xl">Nueva contraseña</CardTitle>
        <CardDescription className="text-center">Ingresá tu nueva contraseña</CardDescription>
      </CardHeader>
      <CardContent>
        {success ? (
          <Notice tone="ok" title="Contraseña restablecida">
            Te llevamos a la pantalla de ingreso.
          </Notice>
        ) : (
          <form onSubmit={handleConfirmReset} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="newPassword" className="text-sm font-medium">
                {branding.texts.passwordLabel}
              </label>
              <Input
                id="newPassword"
                type="password"
                placeholder={branding.texts.passwordPlaceholder}
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                required
                disabled={loading}
                minLength={8}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="confirmPassword" className="text-sm font-medium">
                {branding.texts.confirmPasswordLabel}
              </label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder={branding.texts.passwordPlaceholder}
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                required
                disabled={loading}
                minLength={8}
              />
            </div>
            {error && <Notice tone="danger" title={error} />}
            <SubmitButton
              loading={loading}
              label={loading ? 'Restableciendo…' : 'Restablecer contraseña'}
            />
          </form>
        )}
      </CardContent>
    </Card>
  )
}
