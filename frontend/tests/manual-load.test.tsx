/**
 * Cargar a mano la fila que el portal publicó rota, y elegir entre dos valores.
 *
 * Es la otra mitad del Artículo II del lado de la pantalla. Hasta acá una fila
 * de facturas ilegible sólo se podía dar por revisada: quedaba contada y
 * visible —que ya era más de lo que había— y la factura no entraba a ningún
 * total ni al calendario de vencimientos.
 *
 * Tres cosas que sólo existen acá y que ninguna request puede verificar:
 *
 * **La decisión viaja con lo que se escribió.** Es el punto entero: el backend
 * registra la factura con esos cuatro campos, y si el formulario manda otra
 * cosa, entra otra factura.
 *
 * **No se guarda como regla.** Una regla contesta sola la próxima vez que
 * llegue lo mismo, y la próxima fila ilegible va a ser otra factura. Se rompe
 * en silencio: la pantalla seguiría andando, y el sistema aprendería a
 * registrar la misma factura una y otra vez.
 *
 * **Sin el padrón no se ofrece.** Sin proveedor no hay factura que registrar, y
 * un formulario que termina en un 403 es peor que decir quién puede hacerlo.
 */
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { resolveCase } from '@/app/actions/triage'
import { CaseDetail } from '@/components/triage/CaseDetail'
import type { Supplier } from '@/lib/purchases/types'
import type { Case } from '@/lib/triage/types'

vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh: vi.fn() }) }))
vi.mock('@/app/actions/triage', () => ({ resolveCase: vi.fn() }))
vi.mock('@/components/ui/toast', () => ({ useToast: () => ({ addToast: vi.fn() }) }))

const FERRUM = { id: 4, legal_name: 'Ferrum Andina SA' } as Supplier

function unCaso(overrides: Partial<Case>): Case {
  return {
    id: 31,
    kind: 'unreadable_invoice_row',
    reason: 'La fila de facturas no se pudo interpretar',
    payload: {
      excerpt: 'FC A 0001-00099999   ???   $ --',
      origin: 'facturas',
    },
    section: 'PURCHASING',
    status: 'PENDING',
    batch_id: 4,
    occurrences: 3,
    decision: null,
    resolved_by_user_id: null,
    resolved_by_name: null,
    resolved_at: null,
    created_at: '2026-09-01T03:54:54Z',
    waiting_days: 0,
    is_stale: false,
    ...overrides,
  } as unknown as Case
}

const LA_FILA = unCaso({})
const LA_DISCUSION = unCaso({
  id: 32,
  kind: 'disputed_invoice',
  reason: 'La cargó una persona y el portal la publicó distinta',
  payload: {
    entity: 'invoice',
    entity_id: 9,
    number: '0001-00099999',
    supplier_text: 'Ferrum Andina SA',
    typed: { fecha: '2026-08-30', total: '152400' },
    published: { fecha: '2026-08-30', total: '160000' },
    origin: 'facturas',
  },
})

function dibujar(item: Case, suppliers: Supplier[] = [FERRUM]) {
  return render(<CaseDetail item={item} mayCorrect={false} categories={[]} suppliers={suppliers} />)
}

describe('una fila de facturas que nadie pudo leer', () => {
  beforeEach(() => {
    vi.mocked(resolveCase).mockReset()
    vi.mocked(resolveCase).mockResolvedValue({ ok: true, data: LA_FILA })
  })

  it('se puede cargar a mano, y la carga viaja con lo que se escribió', async () => {
    const persona = userEvent.setup()
    dibujar(LA_FILA)

    await persona.click(screen.getByRole('button', { name: 'Siguiente' }))
    await persona.click(screen.getByRole('button', { name: /Cargarla a mano/ }))

    await persona.type(screen.getByLabelText('Número'), '0001-00099999')
    fireEvent.change(screen.getByLabelText('Fecha de emisión'), {
      target: { value: '2026-08-30' },
    })
    await persona.selectOptions(screen.getByLabelText('Proveedor'), '4')
    await persona.type(screen.getByLabelText('Total'), '152400')

    await persona.click(screen.getByRole('button', { name: 'Siguiente' }))
    await persona.click(screen.getByRole('button', { name: 'Cargar la factura' }))

    // El tercer argumento es `remember`, y va en falso: la próxima fila
    // ilegible va a ser otra factura, no ésta otra vez.
    expect(resolveCase).toHaveBeenCalledWith(
      31,
      {
        action: 'load',
        number: '0001-00099999',
        issued_on: '2026-08-30',
        total: '152400',
        supplier_id: 4,
      },
      false
    )
  })

  it('sin el padrón no ofrece cargar nada, y dice quién puede', async () => {
    const persona = userEvent.setup()
    dibujar(LA_FILA, [])

    await persona.click(screen.getByRole('button', { name: 'Siguiente' }))
    await persona.click(screen.getByRole('button', { name: /Cargarla a mano/ }))

    expect(screen.getByText(/Puede hacerlo compras o el dueño/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
  })

  it('darla por revisada sigue estando, para cuando el papel no está', async () => {
    const persona = userEvent.setup()
    dibujar(LA_FILA)

    await persona.click(screen.getByRole('button', { name: 'Siguiente' }))
    await persona.click(screen.getByRole('button', { name: /Darlo por revisado/ }))
    await persona.click(screen.getByRole('button', { name: 'Siguiente' }))
    await persona.click(screen.getByRole('button', { name: 'Darlo por revisado' }))

    // Ésta sí se guarda como regla, que es lo que ya hacía: darla por revisada
    // es la decisión de siempre sobre una fila que el origen publicó rota.
    expect(resolveCase).toHaveBeenCalledWith(31, { action: 'ignore' }, true)
  })
})

describe('la factura que el portal publicó distinta de lo cargado', () => {
  beforeEach(() => {
    vi.mocked(resolveCase).mockReset()
    vi.mocked(resolveCase).mockResolvedValue({ ok: true, data: LA_DISCUSION })
  })

  it('muestra los dos valores, sin elegir ninguno de antemano', async () => {
    const persona = userEvent.setup()
    dibujar(LA_DISCUSION)

    await persona.click(screen.getByRole('button', { name: 'Siguiente' }))

    // Los dos, con la plata escrita como plata: es la única forma de contestar
    // la pregunta mirando la pantalla.
    expect(screen.getByRole('button', { name: /152\.400/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /160\.000/ })).toBeInTheDocument()
    // Y no se puede avanzar sin elegir: el sistema no decide esto solo.
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
  })

  it('manda cuál de los dos queda', async () => {
    const persona = userEvent.setup()
    dibujar(LA_DISCUSION)

    await persona.click(screen.getByRole('button', { name: 'Siguiente' }))
    await persona.click(screen.getByRole('button', { name: /Queda lo que publicó el portal/ }))
    await persona.click(screen.getByRole('button', { name: 'Siguiente' }))
    await persona.click(screen.getByRole('button', { name: 'Queda lo que publicó el portal' }))

    expect(resolveCase).toHaveBeenCalledWith(32, { keep: 'portal' }, false)
  })
})
