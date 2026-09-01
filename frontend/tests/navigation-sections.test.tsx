/**
 * `RF-03`, `RF-04`, `RF-17`, `RF-18` y `RF-22`: la barra lateral muestra sólo lo
 * que quien mira puede abrir, y muestra **todo** lo que puede abrir.
 *
 * Va con dos accesos y no con uno, que es lo que hace que el test pruebe algo:
 * con el del dueño no se esconde nada, así que `RF-17`, `RF-18` y `RF-22`
 * pasarían por omisión sin que nadie hubiera escrito el filtrado.
 */
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Navigation } from '@/components/auth/Navigation'
import type { Permissions } from '@/lib/auth/permissions'
import type { components } from '@/lib/api/types'

vi.mock('next/navigation', () => ({ usePathname: () => '/tablero' }))
vi.mock('@/app/actions/auth', () => ({ logoutAction: vi.fn() }))

const USER = { id: 1, name: 'Marcela', last_name: 'Díaz' } as components['schemas']['UserRead']

/** El dueño: alcanza todas las secciones, que es el menú más largo posible. */
const DUENO = new Proxy({}, { get: () => 2 }) as unknown as Permissions

/** Julián, que trabaja en ventas y no tiene por qué ver las compras. */
const VENTAS: Permissions = { SALES: 2, DASHBOARD: 1 }

/** Las dieciséis secciones, en el orden en que la barra las nombra. */
const LAS_DIECISEIS = [
  'Tablero',
  'Proveedores',
  'Facturas',
  'Órdenes de compra',
  'Calendario',
  'Mensajes',
  'Ventas',
  'Catálogo y precios',
  'Rubros',
  'Revisar esto',
  'Acciones',
  'Historial',
  'Accesos',
  'Actividad',
  'Parámetros',
  'Salud',
]

/** Los enlaces de secciones: el del pie —la ficha de la persona— no lo es. */
function secciones() {
  return within(screen.getByRole('navigation'))
    .getAllByRole('link')
    .map(link => link.textContent)
}

describe('la barra lateral', () => {
  it('con el acceso del dueño lista las dieciséis secciones, Ventas entre ellas', () => {
    render(<Navigation user={USER} permissions={DUENO} />)

    expect(secciones()).toEqual(LAS_DIECISEIS)
    // RF-22: Ventas es una entrada más, y lleva al área, no a una pantalla.
    expect(screen.getByRole('link', { name: 'Ventas' })).toHaveAttribute('href', '/ventas')
  })

  it('con un acceso de Ventas no aparecen Facturas, Órdenes ni Accesos', () => {
    render(<Navigation user={USER} permissions={VENTAS} />)

    // Las cuatro últimas no nombran sección: cualquier sesión las alcanza, y
    // cada una recorta adentro lo que muestra.
    expect(secciones()).toEqual([
      'Tablero',
      'Ventas',
      'Revisar esto',
      'Acciones',
      'Historial',
      'Salud',
    ])
    for (const ajena of ['Facturas', 'Órdenes de compra', 'Accesos', 'Parámetros']) {
      expect(screen.queryByRole('link', { name: ajena })).toBeNull()
    }
  })

  it('RF-18 · un grupo sin ninguna entrada visible no muestra su título', () => {
    render(<Navigation user={USER} permissions={VENTAS} />)

    // Compras se queda sin una sola entrada: el título tampoco tiene que estar.
    expect(screen.queryByText('Compras')).toBeNull()
    // Ventas sí tiene la suya, así que su título sigue.
    expect(screen.getByText('Ventas', { selector: 'p' })).toBeInTheDocument()
  })

  it('RF-04 · el nombre de quien trabaja y la salida se ven sin abrir nada', () => {
    render(<Navigation user={USER} permissions={VENTAS} />)

    expect(screen.getByText('Marcela Díaz')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cerrar sesión' })).toBeInTheDocument()
  })
})
