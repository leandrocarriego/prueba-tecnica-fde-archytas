import { redirect } from 'next/navigation'
import { getCurrentUser } from '@/app/actions/auth'
import { AuthBrandingProvider } from '@/components/auth/AuthBrandingProvider'
import { AuthLayout } from '@/components/auth/AuthLayout'
import { LoginForm } from '@/components/auth/LoginForm'

export default async function LoginPage() {
  // Si ya está autenticado, redirigir a la página principal
  const user = await getCurrentUser()
  if (user) {
    redirect('/')
  }

  return (
    <AuthBrandingProvider>
      <AuthLayout>
        <LoginForm />
      </AuthLayout>
    </AuthBrandingProvider>
  )
}
