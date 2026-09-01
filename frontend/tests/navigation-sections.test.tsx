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

/**
 * Las doce secciones, en el orden en que la barra las nombra.
 *
 * **«Para decidir» va segunda, pegada al Tablero**, y no dentro de un grupo: no
 * es de un área —lleva lo apartado de ventas, de compras y del padrón—, y con
 * el tablero forma el par con el que se abre el día.
 *
 * Accesos y Parámetros dejaron de ser dos entradas: son dos pestañas de
 * «Configuración», que es una sola. Por eso son doce y no trece.
 */
const LAS_DOCE = [
  'Tablero',
  'Para decidir',
  'Proveedores',
  'Facturas',
  'Órdenes de compra',
  'Calendario',
  'Ventas',
  'Catálogo y precios',
  'Rubros',
  'Actividad',
  'Configuración',
  'Salud',
]

/** Los enlaces de secciones: el del pie —la ficha de la persona— no lo es. */
function secciones() {
  return within(screen.getByRole('navigation'))
    .getAllByRole('link')
    .map(link => link.textContent)
}

describe('la barra lateral', () => {
  it('con el acceso del dueño lista las doce secciones, Ventas entre ellas', () => {
    render(<Navigation user={USER} permissions={DUENO} />)

    expect(secciones()).toEqual(LAS_DOCE)
    // RF-22: Ventas es una entrada más, y lleva al área, no a una pantalla.
    expect(screen.getByRole('link', { name: 'Ventas' })).toHaveAttribute('href', '/ventas')
  })

  it('con un acceso de Ventas no aparecen Facturas, Órdenes ni Configuración', () => {
    render(<Navigation user={USER} permissions={VENTAS} />)

    // «Para decidir», «Actividad» y «Salud» no nombran sección: cualquier
    // sesión las alcanza, y cada una recorta adentro lo que muestra.
    expect(secciones()).toEqual(['Tablero', 'Para decidir', 'Ventas', 'Actividad', 'Salud'])
    // Configuración es una entrada sola y sigue siendo del dueño: quien no
    // llega a los parámetros no la ve, como no veía «Accesos» ni «Parámetros».
    for (const ajena of ['Facturas', 'Órdenes de compra', 'Configuración', 'Rubros']) {
      expect(screen.queryByRole('link', { name: ajena })).toBeNull()
    }
  })

  it('RF-18 · un grupo sin ninguna entrada visible no muestra su título', () => {
    render(<Navigation user={USER} permissions={VENTAS} />)

    // Compras se queda sin una sola entrada: el título tampoco tiene que estar.
    expect(screen.queryByText('Compras')).toBeNull()
    // «Catálogo y datos» conserva a Ventas, así que su título sigue. Ventas ya
    // no es un grupo: es la primera entrada de éste. La cola se fue de acá
    // arriba, pegada al tablero, porque no es del catálogo.
    expect(screen.getByText('Catálogo y datos', { selector: 'p' })).toBeInTheDocument()
    expect(screen.queryByText('Ventas', { selector: 'p' })).toBeNull()
  })

  it('avisa cuántos esperan una decisión, sin que haya que entrar a mirar', () => {
    render(<Navigation user={USER} permissions={DUENO} counters={{ triage: 12 }} />)

    // El número va sobre la entrada, que es el único lugar donde se ve desde
    // cualquier pantalla: quien está mirando una factura se entera igual.
    const entrada = screen.getByRole('link', { name: /Para decidir/ })
    expect(entrada).toHaveTextContent('12')
  })

  it('sin pendientes no dibuja ninguna señal', () => {
    render(<Navigation user={USER} permissions={DUENO} counters={{ triage: 0 }} />)

    // Un contador en cero es una alarma apagada que igual ocupa lugar: a la
    // semana nadie distingue ninguno de los dos estados.
    expect(screen.getByRole('link', { name: 'Para decidir' })).toHaveTextContent(/^Para decidir$/)
  })

  it('RF-04 · el nombre de quien trabaja y la salida se ven sin abrir nada', () => {
    render(<Navigation user={USER} permissions={VENTAS} />)

    expect(screen.getByText('Marcela Díaz')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cerrar sesión' })).toBeInTheDocument()
  })
})
