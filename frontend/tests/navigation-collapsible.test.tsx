/**
 * RF-41 de la 006: la barra lateral se pliega en un teléfono.
 *
 * El defecto que este test congela lo encontró la verificación a mano de la
 * 006 (`docs/specs/006-due-date-calendar/evidence/`): la barra apilada medía
 * 832px sobre un viewport de 664px, así que al abrir el calendario en un
 * teléfono la primera pantalla entera era el menú y había que desplazarse una
 * pantalla y media para ver el primer vencimiento.
 *
 * Lo que se puede fijar acá es la conducta —cerrada por omisión, se abre, se
 * cierra sola al navegar—. Que **se vea** bien en un teléfono no lo demuestra
 * ningún test: eso se verifica a mano, y está en `evidence/`.
 */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { Navigation } from '@/components/auth/Navigation'
import type { Permissions } from '@/lib/auth/permissions'
import type { components } from '@/lib/api/types'

const pathname = vi.fn(() => '/calendario')
vi.mock('next/navigation', () => ({ usePathname: () => pathname() }))
vi.mock('@/app/actions/auth', () => ({ logoutAction: vi.fn() }))

const USER = { id: 1, name: 'Marcela', last_name: 'Díaz' } as components['schemas']['UserRead']
/** El dueño: alcanza todas las secciones, que es el menú más largo posible. */
const TODO = new Proxy({}, { get: () => 2 }) as unknown as Permissions

function menu() {
  return screen.getByRole('navigation').parentElement as HTMLElement
}

describe('la barra lateral en una pantalla angosta', () => {
  it('llega plegada, y el botón dice que está cerrada', () => {
    render(<Navigation user={USER} permissions={TODO} />)

    const boton = screen.getByRole('button', { name: 'Menú' })
    expect(boton).toHaveAttribute('aria-expanded', 'false')
    // `hidden` es lo que la deja plegada; `md:flex` la abre en escritorio, así
    // que en una pantalla ancha el botón no decide nada.
    expect(menu().className).toContain('hidden')
    expect(menu().className).toContain('md:flex')
  })

  it('con el menú cerrado, la franja dice en qué sección está parada la persona', () => {
    render(<Navigation user={USER} permissions={TODO} />)

    // Dos veces: el enlace del menú y el rótulo de la franja. Sin el rótulo,
    // plegada, la pantalla no diría dónde está.
    expect(screen.getAllByText('Calendario')).toHaveLength(2)
  })

  it('el botón la abre y la vuelve a cerrar', async () => {
    const user = userEvent.setup()
    render(<Navigation user={USER} permissions={TODO} />)

    await user.click(screen.getByRole('button', { name: 'Menú' }))
    const abierto = screen.getByRole('button', { name: 'Cerrar' })
    expect(abierto).toHaveAttribute('aria-expanded', 'true')
    expect(menu().className).not.toContain('hidden')

    await user.click(abierto)
    expect(screen.getByRole('button', { name: 'Menú' })).toHaveAttribute('aria-expanded', 'false')
  })

  it('el botón nombra el panel que abre', () => {
    render(<Navigation user={USER} permissions={TODO} />)

    expect(screen.getByRole('button', { name: 'Menú' })).toHaveAttribute(
      'aria-controls',
      'menu-principal'
    )
    expect(menu()).toHaveAttribute('id', 'menu-principal')
  })
})
