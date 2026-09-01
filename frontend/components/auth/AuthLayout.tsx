'use client'

import { ReactNode } from 'react'

import { useBranding } from './AuthBrandingProvider'

interface AuthLayoutProps {
  children: ReactNode
}

/**
 * La forma de las pantallas de sesión: el panel de identidad y, al lado, lo que
 * la persona vino a hacer (`docs/design/` 3m, `RF-05`).
 *
 * **La tarjeta es ésta**, y por eso lo que va adentro no trae la suya: el panel
 * en tinta grafito con el sello, el nombre del negocio y la bajada es lo que
 * hace que el ingreso se vea como la plataforma y no como un formulario
 * cualquiera. Antes había tres variantes de layout —centrada, partida, ancho
 * completo— con imágenes de fondo y una flecha circular: andamio de una
 * plantilla, del que sólo se usaba la centrada.
 *
 * En pantalla angosta el panel se acuesta arriba en vez de desaparecer: es la
 * marca, y es lo primero que ve alguien que abre el enlace de una invitación.
 *
 * Nota: lo que tenga que sobrevivir a la navegación entre login y
 * reset-password va en `app/(auth)/layout.tsx`, no acá.
 */
export function AuthLayout({ children }: AuthLayoutProps) {
  const { colors, logo, business } = useBranding()

  return (
    <div
      className="flex min-h-dvh flex-col justify-center p-6"
      style={{ backgroundColor: colors.background }}
    >
      <div className="mx-auto w-full max-w-2xl overflow-hidden rounded-lg border border-border bg-card sm:grid sm:grid-cols-[12rem_1fr]">
        <div className="flex flex-col justify-between gap-8 bg-primary p-6">
          <span
            aria-hidden
            className="flex size-10 items-center justify-center rounded-md border-[1.5px] border-brand text-sm font-bold text-primary-foreground"
          >
            {logo.text}
          </span>
          <div>
            <p className="text-[15px] leading-snug font-semibold text-primary-foreground">
              {business.name}
            </p>
            {/* La bajada va en mono, como todo rótulo de la guía. */}
            <p className="mt-1.5 font-mono text-xs text-primary-foreground/50">
              {business.tagline}
            </p>
          </div>
        </div>

        <div className="flex flex-col justify-center p-6 sm:p-7">{children}</div>
      </div>
    </div>
  )
}
