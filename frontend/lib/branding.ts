/**
 * La identidad de las pantallas de sesión: colores, marca y textos.
 *
 * Es un archivo de datos, no de aspecto. **La forma la pone `AuthLayout`** y es
 * una sola —el panel de identidad y el formulario al lado, como en
 * `docs/design/` (3m)—, así que acá ya no hay variantes de layout ni opciones
 * de tarjeta: eran andamio de una plantilla genérica que nadie usaba y que hacía
 * que el ingreso se viera como cualquier producto menos como éste.
 */

export interface BrandingColors {
  primary: string
  primaryHover: string
  /** El texto que va encima de `primary`. Es paleta, no un blanco cualquiera. */
  primaryForeground: string
  background: string
  cardBackground: string
  text: string
  textSecondary: string
  border: string
  error: string
  success: string
}

export interface BrandingLogo {
  /** El sello del panel: dos letras. Lo dibuja `AuthLayout`. */
  text: string
  alt?: string
}

/** De quién es la plataforma, tal como se lee en el panel de identidad. */
export interface BrandingBusiness {
  name: string
  /** La bajada del panel: qué es esto, en tres palabras. */
  tagline: string
}

export interface BrandingTexts {
  loginTitle: string
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
}

export interface AuthBrandingConfig {
  colors: BrandingColors
  logo: BrandingLogo
  business: BrandingBusiness
  texts: BrandingTexts
}

/**
 * Branding for the authentication pages (colors, logo, copy).
 * There is a single configuration: this file.
 */
export const brandingConfig: AuthBrandingConfig = {
  colors: {
    // La paleta de la guía visual (`docs/design/`), **por referencia**: cada
    // color es el token de `app/globals.css`, no una copia de su valor.
    //
    // Antes acá estaban los seis hex escritos de nuevo, con la advertencia de
    // que si se cambiaba la paleta había que cambiar los dos lugares. Una
    // advertencia no es un mecanismo: el día que cambie el naranja, las
    // pantallas de sesión iban a quedar con el viejo y nadie se iba a enterar
    // hasta verlas. `var(--brand)` sirve igual como string en un estilo en
    // línea, y ya no hay dos fuentes que puedan discrepar (`UI-01`).
    primary: 'var(--brand)',
    primaryHover: 'var(--brand-hover)',
    primaryForeground: 'var(--brand-foreground)',
    background: 'var(--background)',
    cardBackground: 'var(--card)',
    text: 'var(--foreground)',
    textSecondary: 'var(--muted-foreground)',
    border: 'var(--border)',
    error: 'var(--destructive)',
    success: 'var(--ok)',
  },
  logo: {
    text: 'FC',
    alt: 'Ferretería Industrial Cordillera',
  },
  business: {
    name: 'Ferretería Industrial Cordillera',
    tagline: 'Gestión interna',
  },
  texts: {
    loginTitle: 'Entrar',
    loginButton: 'Ingresar',
    resetPasswordTitle: 'Recuperar el acceso',
    // El enlace **sale por WhatsApp**, al número registrado del acceso: el
    // email es sólo con lo que se identifica quien lo pide.
    resetPasswordSubtitle:
      'Poné el email con el que entrás y te mandamos el enlace por WhatsApp, al número que tenés registrado.',
    resetPasswordButton: 'Mandarme el enlace',
    forgotPasswordLink: 'Olvidé mi contraseña',
    backToLogin: 'Volver al ingreso',
    emailLabel: 'Email',
    passwordLabel: 'Contraseña',
    confirmPasswordLabel: 'Repetir la contraseña',
    emailPlaceholder: 'nombre@cordillera.com.ar',
    passwordPlaceholder: '••••••••',
  },
}

/**
 * Branding configuration used by the auth pages.
 * Single source of truth: edit the object above to restyle login / reset-password.
 */
export function getBrandingConfig(): AuthBrandingConfig {
  return brandingConfig
}
