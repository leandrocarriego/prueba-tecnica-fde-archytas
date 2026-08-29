'use client'

import { loginAction } from '@/app/actions/auth'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { useFormStatus } from 'react-dom'
import { useBranding } from './AuthBrandingProvider'

interface LoginFormProps {
  className?: string
  renderLogo?: (config: ReturnType<typeof useBranding>) => React.ReactNode
  renderFooter?: (config: ReturnType<typeof useBranding>) => React.ReactNode
}

/**
 * Submit button.
 *
 * It is a child component because `useFormStatus` only reports the pending
 * state of a form it is rendered inside — reading it from the form component
 * itself would always return false.
 */
function SubmitButton({ branding }: { branding: ReturnType<typeof useBranding> }) {
  const { pending } = useFormStatus()

  return (
    <Button
      type="submit"
      disabled={pending}
      className="w-full cursor-pointer rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
      style={{
        backgroundColor: branding.colors.primary,
        color: '#ffffff',
      }}
      onMouseEnter={e => {
        if (!pending) {
          e.currentTarget.style.backgroundColor = branding.colors.primaryHover
        }
      }}
      onMouseLeave={e => {
        if (!pending) {
          e.currentTarget.style.backgroundColor = branding.colors.primary
        }
      }}
    >
      {pending ? 'Iniciando sesión...' : branding.texts.loginButton}
    </Button>
  )
}

/**
 * Login form.
 * Provides functionality without hardcoded styles.
 * Styles and layout can be customized via branding config.
 *
 * Uses loginAction directly as form action to allow redirect() to work correctly.
 */
export function LoginForm({ className, renderLogo, renderFooter }: LoginFormProps) {
  const branding = useBranding()
  const searchParams = useSearchParams()
  // The server action redirects back with `?error=` on failure, so the query
  // string is the only source of error state: there is nothing to keep locally.
  const error = searchParams.get('error')

  // Card styling from branding config
  const cardRounded =
    branding.formOptions?.cardStyle?.rounded === 'xl'
      ? 'rounded-xl'
      : branding.formOptions?.cardStyle?.rounded === '2xl'
        ? 'rounded-2xl'
        : branding.formOptions?.cardStyle?.rounded === 'lg'
          ? 'rounded-lg'
          : branding.formOptions?.cardStyle?.rounded === 'md'
            ? 'rounded-md'
            : branding.formOptions?.cardStyle?.rounded === 'sm'
              ? 'rounded-sm'
              : 'rounded-lg'

  const cardShadow =
    branding.formOptions?.cardStyle?.shadow === 'xl'
      ? 'shadow-xl'
      : branding.formOptions?.cardStyle?.shadow === 'lg'
        ? 'shadow-lg'
        : branding.formOptions?.cardStyle?.shadow === 'md'
          ? 'shadow-md'
          : branding.formOptions?.cardStyle?.shadow === 'sm'
            ? 'shadow-sm'
            : branding.formOptions?.cardStyle?.shadow === 'none'
              ? 'shadow-none'
              : 'shadow-sm'

  return (
    <Card
      className={cn(className, cardRounded, cardShadow)}
      style={{
        backgroundColor: branding.colors.cardBackground,
        borderColor: branding.colors.border,
      }}
    >
      <CardHeader className="space-y-1">
        {renderLogo && renderLogo(branding)}
        <CardTitle
          className={`text-2xl ${branding.formOptions?.textAlignment === 'left' ? 'text-left' : 'text-center'}`}
          style={{ color: branding.colors.text }}
        >
          {branding.texts.loginTitle}
        </CardTitle>
        <CardDescription
          className={branding.formOptions?.textAlignment === 'left' ? 'text-left' : 'text-center'}
          style={{ color: branding.colors.textSecondary }}
        >
          {branding.texts.loginSubtitle}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form action={loginAction} className="space-y-5">
          {error && (
            <div
              className="p-3 rounded-lg text-sm"
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#dc2626',
              }}
            >
              {error}
            </div>
          )}
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
              name="email"
              type="email"
              placeholder={branding.texts.emailPlaceholder}
              required
              className="rounded-lg"
            />
          </div>
          <div className="space-y-2">
            <label
              htmlFor="password"
              className="text-sm font-medium"
              style={{ color: branding.colors.text }}
            >
              {branding.texts.passwordLabel}
            </label>
            <Input
              id="password"
              name="password"
              type="password"
              placeholder={branding.texts.passwordPlaceholder}
              required
              className="rounded-lg"
            />
          </div>
          {/* Remember me checkbox - optional, shown if needed */}
          {branding.formOptions?.showRememberMe && (
            <div className="flex items-center justify-between">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  name="remember"
                  defaultChecked={true}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  style={{ accentColor: branding.colors.primary }}
                />
                <span className="text-sm" style={{ color: branding.colors.text }}>
                  {branding.texts.rememberMe || 'Recordarme'}
                </span>
              </label>
              <Link
                href="/reset-password"
                className="text-sm hover:underline"
                style={{ color: branding.colors.primary }}
              >
                {branding.texts.forgotPasswordLink}
              </Link>
            </div>
          )}
          <SubmitButton branding={branding} />
          {renderFooter && renderFooter(branding)}
        </form>
      </CardContent>
    </Card>
  )
}
