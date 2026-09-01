/**
 * La cola de «Para decidir», del lado que sólo existe en la pantalla.
 *
 * El diseño firmado (guía visual `3d`) pide maestro-detalle: la lista angosta a
 * la izquierda, un solo caso abierto a la derecha. Eso trae tres reglas que
 * ninguna request puede verificar, y que se rompen en silencio:
 *
 * **Se abre uno solo, y elegir otro lo cambia.** Es la forma entera: si la
 * elección no cambiara el panel, la pantalla sería la pila de tarjetas que
 * había antes con un menú al costado.
 *
 * **Lo escrito en un caso no se arrastra al siguiente.** El precio a medio
 * tipear y el rubro elegido son estado del caso que se estaba resolviendo. Sin
 * el `key` sobre el detalle, React reusa el componente y el número queda puesto
 * sobre otro caso — que es la manera más silenciosa de registrar un precio en
 * el producto equivocado.
 *
 * **El caso abierto puede desaparecer.** Se resolvió, o lo resolvió otra
 * persona y la página se refrescó. La selección se deriva de la lista, así que
 * la cola sigue mostrando algo en vez de quedarse en blanco.
 */
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { resolveCase } from '@/app/actions/triage'
import { CaseQueue } from '@/components/triage/CaseQueue'
import type { Case } from '@/lib/triage/types'

vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh: vi.fn() }) }))
vi.mock('@/app/actions/triage', () => ({ resolveCase: vi.fn() }))
vi.mock('@/components/ui/toast', () => ({ useToast: () => ({ addToast: vi.fn() }) }))

function unCaso(overrides: Partial<Case>): Case {
  return {
    id: 1,
    kind: 'unreadable_row',
    reason: 'La fila no traía un precio que se pudiera leer',
    payload: { product_code: 'FC-1071', price: '1500' },
    section: 'PURCHASING',
    status: 'PENDING',
    batch_id: 4,
    occurrences: 1,
    decision: null,
    resolved_by_user_id: null,
    resolved_by_name: null,
    resolved_at: null,
    created_at: '2026-08-31T10:00:00Z',
    waiting_days: 2,
    is_stale: false,
    ...overrides,
  } as unknown as Case
}

const LA_FILA = unCaso({})
const EL_PRODUCTO = unCaso({
  id: 2,
  kind: 'missing_product',
  reason: 'Un producto que dejó de figurar en la lista',
  payload: { product_code: 'FC-2000' },
  // Once días antes que la fila: es lo que hace que ordenar se note.
  created_at: '2026-08-20T10:00:00Z',
  waiting_days: 13,
  is_stale: true,
})

const LOS_DOS = [LA_FILA, EL_PRODUCTO]

function dibujar(items: Case[]) {
  return render(
    <CaseQueue
      items={items}
      pendingTotal={items.length}
      mayCorrect={false}
      categories={[]}
      suppliers={[]}
    />
  )
}

describe('la cola de pendientes', () => {
  beforeEach(() => {
    vi.mocked(resolveCase).mockReset()
  })

  it('abre el primero y cambia de caso cuando se elige otro', async () => {
    const persona = userEvent.setup()
    dibujar(LOS_DOS)

    // El primero del orden que trae el backend: el último que llegó.
    expect(screen.getByRole('heading', { name: LA_FILA.reason })).toBeInTheDocument()

    await persona.click(screen.getByRole('button', { name: /Producto que dejó de figurar/ }))

    expect(screen.getByRole('heading', { name: EL_PRODUCTO.reason })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: LA_FILA.reason })).toBeNull()
    // Y con el caso cambia la decisión que se ofrece: cada clase tiene la suya.
    await persona.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(screen.getByRole('button', { name: /Darlo por discontinuado/ })).toBeInTheDocument()
  })

  it('no arrastra al caso siguiente lo que se escribió en el anterior', async () => {
    const persona = userEvent.setup()
    dibujar(LOS_DOS)

    // Un precio tipeado a mano sobre la fila ilegible, y no se confirma.
    await persona.click(screen.getByRole('button', { name: 'Siguiente' }))
    await persona.clear(screen.getByLabelText('Precio'))
    await persona.type(screen.getByLabelText('Precio'), '999')

    await persona.click(screen.getByRole('button', { name: /Producto que dejó de figurar/ }))
    await persona.click(screen.getByRole('button', { name: /Fila que no se pudo interpretar/ }))
    await persona.click(screen.getByRole('button', { name: 'Siguiente' }))

    // Vuelve a decir lo que trajo el portal, no lo que quedó a medio escribir.
    expect(screen.getByLabelText('Precio')).toHaveValue(1500)
  })

  it('si el caso abierto ya no está, abre el que quedó', async () => {
    const persona = userEvent.setup()
    const { rerender } = dibujar(LOS_DOS)

    await persona.click(screen.getByRole('button', { name: /Producto que dejó de figurar/ }))

    // Se resolvió, y la página refrescada trae la cola sin él.
    rerender(
      <CaseQueue
        items={[LA_FILA]}
        pendingTotal={1}
        mayCorrect={false}
        categories={[]}
        suppliers={[]}
      />
    )

    expect(screen.getByRole('heading', { name: LA_FILA.reason })).toBeInTheDocument()
  })

  it('ordenar cambia la lista, y no de adorno', async () => {
    const persona = userEvent.setup()
    dibujar(LOS_DOS)

    await persona.selectOptions(screen.getByLabelText('Ordenar'), 'oldest')

    // El más viejo pasa a encabezar la lista, y con él se abre el panel: sin
    // nadie que haya elegido un caso, el abierto es el primero del orden.
    const [primero] = within(screen.getByRole('list')).getAllByRole('button')
    expect(primero).toHaveTextContent('Producto que dejó de figurar')
    expect(screen.getByRole('heading', { name: EL_PRODUCTO.reason })).toBeInTheDocument()
  })

  it('el paso 3 dice qué se mueve, y recién ahí resuelve', async () => {
    const persona = userEvent.setup()
    vi.mocked(resolveCase).mockResolvedValue({ ok: true, data: LA_FILA })
    dibujar(LOS_DOS)

    await persona.click(screen.getByRole('button', { name: 'Siguiente' }))
    await persona.clear(screen.getByLabelText('Precio'))
    await persona.type(screen.getByLabelText('Precio'), '999')
    await persona.click(screen.getByRole('button', { name: 'Siguiente' }))

    // Antes de confirmar, la pantalla dice qué queda registrado y sobre qué
    // código: es la mitad del asistente que no existía.
    expect(screen.getByText('Qué pasa si confirmás')).toBeInTheDocument()
    expect(screen.getByText(/FC-1071 queda con ese precio/)).toBeInTheDocument()
    expect(resolveCase).not.toHaveBeenCalled()

    await persona.click(screen.getByRole('button', { name: 'Registrar este precio' }))

    expect(resolveCase).toHaveBeenCalledWith(1, { product_code: 'FC-1071', price: '999' }, true)
  })

  it('la cola vacía no dibuja nada: el vacío lo dice la pantalla', () => {
    const { container } = dibujar([])

    expect(container).toBeEmptyDOMElement()
  })
})
