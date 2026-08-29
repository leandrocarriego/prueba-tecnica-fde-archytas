import { Suspense } from 'react'
import { AuthBrandingProvider } from '@/components/auth/AuthBrandingProvider'
import { AuthLayout } from '@/components/auth/AuthLayout'
import { ResetPasswordForm } from '@/components/auth/ResetPasswordForm'

export default function ResetPasswordPage() {
  return (
    <AuthBrandingProvider>
      <AuthLayout>
        {/* The form reads useSearchParams(), so it needs a Suspense boundary
            for this page to be statically rendered. */}
        <Suspense fallback={null}>
          <ResetPasswordForm />
        </Suspense>
      </AuthLayout>
    </AuthBrandingProvider>
  )
}
