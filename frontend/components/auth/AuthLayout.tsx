'use client'

import Image from 'next/image'
import { ReactNode } from 'react'
import { useBranding } from './AuthBrandingProvider'

interface AuthLayoutProps {
  children: ReactNode
}

/**
 * Auth layout component that renders different layouts based on branding config.
 * Nota: lo que tenga que sobrevivir a la navegación entre login y reset-password
 * va en `app/(auth)/layout.tsx`, no acá.
 */
export function AuthLayout({ children }: AuthLayoutProps) {
  const branding = useBranding()
  const { layout, colors, logo } = branding

  if (layout.type === 'split-screen') {
    return (
      <div className="flex min-h-screen relative">
        {/* Left side */}
        <div
          className="hidden lg:flex lg:w-1/2 flex-col justify-center items-center p-12"
          style={{ backgroundColor: colors.background }}
        >
          {layout.leftSideContent ? (
            <div className="max-w-md text-center lg:text-left">
              {/* Welcome title - combined */}
              {layout.leftSideContent.title && layout.leftSideContent.subtitle ? (
                <h1 className="text-5xl font-bold mb-8" style={{ color: colors.primary }}>
                  {layout.leftSideContent.title} {layout.leftSideContent.subtitle}
                </h1>
              ) : layout.leftSideContent.title ? (
                <h1 className="text-5xl font-bold mb-8" style={{ color: colors.primary }}>
                  {layout.leftSideContent.title}
                </h1>
              ) : null}
              {/* Brand logo */}
              <div className="mb-8 flex items-center justify-center lg:justify-start">
                {logo.component ? (
                  <logo.component className="h-16 w-auto" />
                ) : logo.src ? (
                  <Image
                    src={logo.src}
                    alt={logo.alt || 'Logo'}
                    width={300}
                    height={72}
                    className="h-16 w-auto"
                    priority
                  />
                ) : logo.text ? (
                  <span className="text-4xl font-bold" style={{ color: colors.primary }}>
                    {logo.text}
                  </span>
                ) : null}
              </div>
              {/* Circular arrow icon */}
              <div className="flex justify-center lg:justify-start mt-12">
                <div
                  className="w-16 h-16 rounded-full border-2 flex items-center justify-center"
                  style={{ borderColor: colors.text }}
                >
                  <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    style={{ color: colors.text }}
                  >
                    <path
                      d="M9 18L15 12L9 6"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              </div>
              {layout.leftSideContent.description && (
                <p className="text-lg mt-8" style={{ color: colors.textSecondary }}>
                  {layout.leftSideContent.description}
                </p>
              )}
              {layout.leftSideContent.image && (
                <div className="mt-8">
                  <Image
                    src={layout.leftSideContent.image}
                    alt="Brand image"
                    width={400}
                    height={300}
                    className="rounded-lg"
                  />
                </div>
              )}
            </div>
          ) : (
            <div className="max-w-md">
              <h1 className="text-4xl font-bold mb-4" style={{ color: colors.primary }}>
                ¡Bienvenido a la Plataforma Cordillera!
              </h1>
            </div>
          )}
        </div>

        {/* Right side with background */}
        <div
          className="flex-1 flex items-center justify-center p-4 relative overflow-hidden"
          style={{
            backgroundImage: layout.backgroundImage ? `url(${layout.backgroundImage})` : undefined,
            backgroundColor: layout.backgroundImage ? undefined : colors.background,
            backgroundSize: layout.backgroundImage ? 'cover' : undefined,
            backgroundPosition: layout.backgroundImage ? 'center' : undefined,
          }}
        >
          {layout.backgroundImage && layout.backgroundOverlay && (
            <div
              className="absolute inset-0"
              style={{
                backgroundColor: layout.backgroundOverlay,
              }}
            />
          )}
          <div className="relative z-10 w-full max-w-lg px-4">{children}</div>
        </div>
      </div>
    )
  }

  if (layout.type === 'full-width') {
    return (
      <div className="min-h-screen p-4 relative" style={{ backgroundColor: colors.background }}>
        <div className="max-w-4xl mx-auto">{children}</div>
      </div>
    )
  }

  // Default: centered layout
  return (
    <div
      className="flex flex-col min-h-screen relative"
      style={{ backgroundColor: colors.background }}
    >
      <div className="flex-1 flex items-center justify-center p-4">{children}</div>
    </div>
  )
}
