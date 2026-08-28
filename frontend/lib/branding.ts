/**
 * Branding configuration for authentication pages.
 *
 * This configuration allows customization of:
 * - Colors and theme
 * - Logo and branding elements
 * - Text content
 * - Layout styles
 * - Background images
 */

export type AuthLayout = 'centered' | 'split-screen' | 'full-width'

export interface BrandingColors {
  primary: string
  primaryHover: string
  secondary?: string
  background: string
  cardBackground: string
  text: string
  textSecondary: string
  border: string
  error: string
  success: string
}

export interface BrandingLogo {
  src?: string
  alt?: string
  component?: React.ComponentType<{ className?: string }>
  text?: string
  size?: 'sm' | 'md' | 'lg'
}

export interface BrandingTexts {
  loginTitle: string
  loginSubtitle: string
  loginButton: string
  resetPasswordTitle: string
  resetPasswordSubtitle: string
  resetPasswordButton: string
  forgotPasswordLink: string
  backToLogin: string
  emailLabel: string
  passwordLabel: string
  confirmPasswordLabel: string
  emailPlaceholder: string
  passwordPlaceholder: string
  rememberMe?: string // Optional "Remember me" checkbox label
}

export interface BrandingFormOptions {
  showRememberMe?: boolean // Show "Remember me" checkbox
  textAlignment?: 'left' | 'center' // Text alignment for titles and descriptions
  cardStyle?: {
    rounded?: 'sm' | 'md' | 'lg' | 'xl' | '2xl'
    shadow?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'none'
  }
}

export interface BrandingLayout {
  type: AuthLayout
  backgroundImage?: string
  backgroundOverlay?: string
  leftSideContent?: {
    title?: string
    subtitle?: string
    description?: string
    image?: string
  }
}

export interface AuthBrandingConfig {
  colors: BrandingColors
  logo: BrandingLogo
  texts: BrandingTexts
  layout: BrandingLayout
  formOptions?: BrandingFormOptions
}

/**
 * Branding for the authentication pages (colors, logo, copy, layout).
 * There is a single configuration: this file.
 */
export const brandingConfig: AuthBrandingConfig = {
  colors: {
    primary: '#2563eb', // blue-600
    primaryHover: '#1d4ed8', // blue-700
    background: '#f9fafb', // gray-50
    cardBackground: '#ffffff', // white
    text: '#111827', // gray-900
    textSecondary: '#6b7280', // gray-500
    border: '#e5e7eb', // gray-200
    error: '#dc2626', // red-600
    success: '#16a34a', // green-600
  },
  logo: {
    text: 'Cordillera',
    size: 'md',
  },
  texts: {
    loginTitle: 'Iniciar Sesión',
    loginSubtitle: 'Ingresa tus credenciales para acceder a la plataforma',
    loginButton: 'Iniciar Sesión',
    resetPasswordTitle: 'Restablecer Contraseña',
    resetPasswordSubtitle: 'Ingresa tu email para recibir un enlace de restablecimiento',
    resetPasswordButton: 'Enviar Enlace',
    forgotPasswordLink: '¿Olvidaste tu contraseña?',
    backToLogin: 'Volver al Login',
    emailLabel: 'Email',
    passwordLabel: 'Contraseña',
    confirmPasswordLabel: 'Confirmar Contraseña',
    emailPlaceholder: 'tu@email.com',
    passwordPlaceholder: '••••••••',
  },
  layout: {
    type: 'centered',
  },
  formOptions: {
    showRememberMe: false,
    textAlignment: 'center',
    cardStyle: {
      rounded: 'md',
      shadow: 'sm',
    },
  },
}

/**
 * Branding configuration used by the auth pages.
 * Single source of truth: edit the object above to restyle login / reset-password.
 */
export function getBrandingConfig(): AuthBrandingConfig {
  return brandingConfig
}
