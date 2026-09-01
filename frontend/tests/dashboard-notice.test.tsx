/**
 * `RF-14`, `RF-15`, `RF-16` y `RF-23`: el aviso va **antes** que el número.
 *
 * Es lo único de esta feature que puede fallar en silencio. Un color equivocado
 * se ve; un aviso que se dibuja **debajo** del importe se sigue viendo bien y
 * sigue diciendo la verdad —sólo que después de que alguien leyó el número y lo
 * copió a un mensaje—. Por eso lo que se afirma acá es el **orden del DOM**, y
 * no que el aviso exista.
 *
 * `RF-16` y `RF-23` dicen lo contrario a propósito, y los dos se prueban con
 * datos que dan cero: en el tablero, cero excluidos **se dice**; fuera del
 * tablero, cero excluidos **no dibuja ningún aviso**.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import DashboardPage from '@/app/(private)/tablero/page'
import { HeldVouchers } from '@/components/purchases/HeldVouchers'
import type { SalesDashboard } from '@/lib/sales/types'

const fetchFromApi = vi.fn()
vi.mock('@/lib/api/server', () => ({ fetchFromApi: (path: string) => fetchFromApi(path) }))
vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh: vi.fn() }) }))

/** Un tablero con lo mínimo que la pantalla lee, y las exclusiones que se pidan. */
function dashboard(excluded: number): SalesDashboard {
  return {
    since: null,
    until: null,
    invoiced: {
      value: '1234567',
      sales: 42,
      excluded,
      merged: 0,
      has_estimates: false,
    },
    by_month: [],
    held_total: 0,
    pending_groups: 0,
    pending_decisions: 0,
  } as SalesDashboard
}

function answerWith(excluded: number) {
  fetchFromApi.mockReset()
  fetchFromApi.mockImplementation((path: string) =>
    path.startsWith('/dashboard/sales')
      ? Promise.resolve(dashboard(excluded))
      : Promise.resolve(null)
  )
}

/** Dónde cae cada uno en el orden del documento. */
function comesBefore(first: Element, second: Element): boolean {
  return Boolean(first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING)
}

describe('el tablero', () => {
  it('RF-14 · con exclusiones, el aviso está antes que el importe, y lleva su acción', async () => {
    answerWith(12)
    render(await DashboardPage({ searchParams: Promise.resolve({}) }))

    const aviso = screen.getByText('Este total deja 12 registros afuera')
    const importe = screen.getByText('$ 1.234.567')

    expect(comesBefore(aviso, importe), 'el aviso tiene que ir arriba del número').toBe(true)
    // RF-15: un aviso sin salida es sólo una queja. La salida es la cola, que
    // es donde se decide desde que `/ventas` pasó a ser un listado.
    expect(screen.getByRole('link', { name: 'Ver cuáles' })).toHaveAttribute(
      'href',
      '/revision?area=SALES'
    )
  })

  it('RF-16 · con cero exclusiones lo dice con todas las letras', async () => {
    answerWith(0)
    render(await DashboardPage({ searchParams: Promise.resolve({}) }))

    expect(screen.getByText(/no se excluyó ningún registro/)).toBeInTheDocument()
    // Y no inventa un aviso: no hay nada de qué avisar.
    expect(screen.queryByText(/deja .* afuera/)).toBeNull()
  })
})

describe('fuera del tablero', () => {
  it('RF-23 · cero apartados no dibuja ningún aviso', () => {
    // La pantalla de comprobantes con la lista vacía: no hay nada que repartir,
    // y eso es la mejor noticia del día, no una advertencia.
    render(<HeldVouchers held={[]} invoicesBySupplier={{}} />)

    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.queryByText(/afuera|excluid/i)).toBeNull()
  })
})
