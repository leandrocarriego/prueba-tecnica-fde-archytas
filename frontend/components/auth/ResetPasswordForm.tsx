'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useBranding } from './AuthBrandingProvider'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface ResetPasswordFormProps {
  className?: string
  onSuccess?: () => void
  renderLogo?: (config: ReturnType<typeof useBranding>) => React.ReactNode
}

/**
 * Reset password form.
 * Provides functionality without hardcoded styles.
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
  // Which half of the flow to show is decided by the token in the URL and
  // never changes while the form is mounted.
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

  const LogoComponent = branding.logo.component

  if (step === 'request') {
    return (
      <Card
        className={className}
        style={{
          backgroundColor: branding.colors.cardBackground,
          borderColor: branding.colors.border,
        }}
      >
        <CardHeader className="space-y-1">
          {renderLogo ? (
            renderLogo(branding)
          ) : (
            <div className="flex items-center justify-center mb-4">
              {LogoComponent ? (
                <LogoComponent className="w-12 h-12" />
              ) : branding.logo.src ? (
                <img
                  src={branding.logo.src}
                  alt={branding.logo.alt || 'Logo'}
                  className={`${branding.logo.size === 'sm' ? 'w-8 h-8' : branding.logo.size === 'lg' ? 'w-16 h-16' : 'w-12 h-12'}`}
                />
              ) : branding.logo.text ? (
                <div
                  className={`${branding.logo.size === 'sm' ? 'w-8 h-8' : branding.logo.size === 'lg' ? 'w-16 h-16' : 'w-12 h-12'} rounded-lg flex items-center justify-center`}
                  style={{ backgroundColor: branding.colors.primary }}
                >
                  <span className="font-bold text-2xl" style={{ color: '#ffffff' }}>
                    {branding.logo.text}
                  </span>
                </div>
              ) : null}
            </div>
          )}
          <CardTitle className="text-2xl text-center" style={{ color: branding.colors.text }}>
            {branding.texts.resetPasswordTitle}
          </CardTitle>
          <CardDescription className="text-center" style={{ color: branding.colors.textSecondary }}>
            {branding.texts.resetPasswordSubtitle}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {success ? (
            <div className="space-y-4">
              <div
                className="p-4 text-sm rounded-md border"
                style={{
                  color: branding.colors.success,
                  backgroundColor: `${branding.colors.success}10`,
                  borderColor: `${branding.colors.success}30`,
                }}
              >
                Si el email existe, se ha enviado un enlace de restablecimiento.
              </div>
              <Button
                onClick={() => router.push('/login')}
                className="w-full cursor-pointer"
                style={{
                  backgroundColor: branding.colors.primary,
                  color: '#ffffff',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.backgroundColor = branding.colors.primaryHover
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.backgroundColor = branding.colors.primary
                }}
              >
                {branding.texts.backToLogin}
              </Button>
            </div>
          ) : (
            <form onSubmit={handleRequestReset} className="space-y-4">
              <div className="space-y-2">
                <label
                  htmlFor="email"
                  className="text-sm font-medium"
                  style={{ color: branding.colors.text }}
                >
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
              {error && (
                <div
                  className="p-3 text-sm rounded-md border"
                  style={{
                    color: branding.colors.error,
                    backgroundColor: `${branding.colors.error}10`,
                    borderColor: `${branding.colors.error}30`,
                  }}
                >
                  {error}
                </div>
              )}
              <Button
                type="submit"
                className="w-full cursor-pointer"
                style={{
                  backgroundColor: branding.colors.primary,
                  color: '#ffffff',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.backgroundColor = branding.colors.primaryHover
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.backgroundColor = branding.colors.primary
                }}
                disabled={loading}
              >
                {loading ? 'Enviando...' : branding.texts.resetPasswordButton}
              </Button>
              <div className="text-center">
                <Link
                  href="/login"
                  className="text-sm hover:underline"
                  style={{ color: branding.colors.primary }}
                >
                  {branding.texts.backToLogin}
                </Link>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card
      className={className}
      style={{
        backgroundColor: branding.colors.cardBackground,
        borderColor: branding.colors.border,
      }}
    >
      <CardHeader className="space-y-1">
        <div className="flex items-center justify-center mb-4">
          {LogoComponent ? (
            <LogoComponent className="w-12 h-12" />
          ) : branding.logo.src ? (
            <img
              src={branding.logo.src}
              alt={branding.logo.alt || 'Logo'}
              className={`${branding.logo.size === 'sm' ? 'w-8 h-8' : branding.logo.size === 'lg' ? 'w-16 h-16' : 'w-12 h-12'}`}
            />
          ) : branding.logo.text ? (
            <div
              className={`${branding.logo.size === 'sm' ? 'w-8 h-8' : branding.logo.size === 'lg' ? 'w-16 h-16' : 'w-12 h-12'} rounded-lg flex items-center justify-center`}
              style={{ backgroundColor: branding.colors.primary }}
            >
              <span className="font-bold text-2xl" style={{ color: '#ffffff' }}>
                {branding.logo.text}
              </span>
            </div>
          ) : null}
        </div>
        <CardTitle className="text-2xl text-center" style={{ color: branding.colors.text }}>
          Nueva Contraseña
        </CardTitle>
        <CardDescription className="text-center" style={{ color: branding.colors.textSecondary }}>
          Ingresa tu nueva contraseña
        </CardDescription>
      </CardHeader>
      <CardContent>
        {success ? (
          <div className="space-y-4">
            <div
              className="p-4 text-sm rounded-md border"
              style={{
                color: branding.colors.success,
                backgroundColor: `${branding.colors.success}10`,
                borderColor: `${branding.colors.success}30`,
              }}
            >
              Contraseña restablecida exitosamente. Redirigiendo al login...
            </div>
          </div>
        ) : (
          <form onSubmit={handleConfirmReset} className="space-y-4">
            <div className="space-y-2">
              <label
                htmlFor="newPassword"
                className="text-sm font-medium"
                style={{ color: branding.colors.text }}
              >
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
              <label
                htmlFor="confirmPassword"
                className="text-sm font-medium"
                style={{ color: branding.colors.text }}
              >
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
            {error && (
              <div
                className="p-3 text-sm rounded-md border"
                style={{
                  color: branding.colors.error,
                  backgroundColor: `${branding.colors.error}10`,
                  borderColor: `${branding.colors.error}30`,
                }}
              >
                {error}
              </div>
            )}
            <Button
              type="submit"
              className="w-full cursor-pointer"
              style={{
                backgroundColor: branding.colors.primary,
                color: '#ffffff',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.backgroundColor = branding.colors.primaryHover
              }}
              onMouseLeave={e => {
                e.currentTarget.style.backgroundColor = branding.colors.primary
              }}
              disabled={loading}
            >
              {loading ? 'Restableciendo...' : 'Restablecer Contraseña'}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  )
}
