/**
 * `RF-05`: las pantallas de sesión tienen la misma identidad visual que el resto.
 *
 * Lo que se puede decidir sin un navegador es lo que este test fija: que el
 * fondo de las pantallas de ingreso sea **el token de la aplicación** y no un
 * color propio, y que el naranja de la marca salga del mismo lugar. Fue así
 * como se separaron la primera vez: `lib/branding.ts` tenía los seis hex
 * copiados, y el día que la paleta cambiara nadie iba a mirar el login.
 *
 * Que **se vea** igual —la tipografía, los radios, el aire— no lo demuestra
 * ningún test en jsdom: eso es el recorrido del `Tester`.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AuthBrandingProvider } from '@/components/auth/AuthBrandingProvider'
import { AuthLayout } from '@/components/auth/AuthLayout'
import { brandingConfig } from '@/lib/branding'

function renderAuth() {
  return render(
    <AuthBrandingProvider>
      <AuthLayout>
        <p>Iniciar sesión</p>
      </AuthLayout>
    </AuthBrandingProvider>
  )
}

describe('las pantallas de sesión', () => {
  it('pintan el fondo con el token de la aplicación, no con un color propio', () => {
    const { container } = renderAuth()
    const marco = container.firstElementChild as HTMLElement

    expect(marco.style.backgroundColor).toBe('var(--background)')
  })

  it('muestran lo que se les da adentro', () => {
    renderAuth()

    expect(screen.getByText('Iniciar sesión')).toBeInTheDocument()
  })

  it('ningún color de la marca está escrito a mano', () => {
    // Cada valor es una referencia a `app/globals.css`. Si alguno vuelve a ser
    // un hex, la paleta pasa a tener dos fuentes y esto falla acá.
    for (const [name, value] of Object.entries(brandingConfig.colors)) {
      expect(value, `${name} tiene que salir de un token`).toMatch(/^var\(--[a-z-]+\)$/)
    }
  })
})
