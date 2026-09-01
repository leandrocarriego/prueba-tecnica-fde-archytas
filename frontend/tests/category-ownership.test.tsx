/**
 * Quién mantiene los rubros (010), del lado que el backend no puede demostrar.
 *
 * Tres cosas que la feature promete y que sólo existen en la pantalla, y que
 * por eso ninguna request puede verificar:
 *
 * **RF-09 y RF-10 — la puerta.** Los rubros le aparecen a compras entre las
 * secciones a las que entra, y le siguen apareciendo a ventas, que los consulta.
 * El backend sabe que los tres alcanzan la sección; que la barra la dibuje con
 * `READ` y no sólo con `WRITE` es de acá, y se rompe en silencio: si la entrada
 * pidiera edición, Julián tendría permiso de lectura y ninguna forma de entrar.
 *
 * **RF-12 — los botones.** «Esconder el botón no alcanza» es cierto y no es lo
 * único: ofrecerle a ventas un botón que el backend le va a rechazar es una
 * pantalla que miente. Con nivel de lectura no hay ninguna acción, y con el de
 * compras están todas.
 *
 * **RF-14 — la forma escrita.** Es lo único que la 010 construyó de cero: la
 * rama `unknown_category` de la tarjeta de la cola. Muestra la forma escrita
 * que llegó, ofrece los rubros y resuelve con `{ category_id }` — y `remember`
 * queda en `true`, que es lo que convierte la decisión en equivalencia (RF-06).
 *
 * Por qué acá y no en la suite de Python: el precedente son los dos tests de
 * pantalla de la 006. Lo que el backend puede afirmar ya está afirmado en
 * `tests/integration/features/test_category_ownership.py`.
 */
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { resolveCase } from '@/app/actions/triage'
import { Navigation } from '@/components/auth/Navigation'
import { CategoryList } from '@/components/categories/CategoryList'
import { CaseCard } from '@/components/triage/CaseCard'
import { READ, WRITE, type Permissions } from '@/lib/auth/permissions'
import { canEdit } from '@/lib/auth/permissions'
import type { Category } from '@/lib/catalog/types'
import type { Case } from '@/lib/triage/types'
import type { components } from '@/lib/api/types'

vi.mock('next/navigation', () => ({
  usePathname: () => '/rubros',
  useRouter: () => ({ refresh: vi.fn() }),
}))
vi.mock('@/app/actions/auth', () => ({ logoutAction: vi.fn() }))
vi.mock('@/app/actions/triage', () => ({ resolveCase: vi.fn() }))
vi.mock('@/app/actions/categories', () => ({
  createCategory: vi.fn(),
  deleteCategory: vi.fn(),
  renameCategory: vi.fn(),
}))
vi.mock('@/components/ui/toast', () => ({ useToast: () => ({ addToast: vi.fn() }) }))

const USER = { id: 1, name: 'Marcela', last_name: 'Díaz' } as components['schemas']['UserRead']

/**
 * Los accesos de las dos personas **sobre esta sección**, como los da la matriz
 * después de la 010: compras la escribe, ventas la lee.
 *
 * Se escriben y no se derivan: la matriz vive en el backend a propósito, y una
 * copia acá sería la segunda fuente que `lib/auth/permissions.ts` evita. Lo que
 * este archivo verifica es qué hace la pantalla **con** un nivel, no cuál es.
 */
const COMPRAS: Permissions = { PRODUCT_CATEGORIES: WRITE, PRICES: WRITE }
const VENTAS: Permissions = { PRODUCT_CATEGORIES: READ, SALES: WRITE }

const UN_RUBRO: Category = { id: 3, name: 'Herramientas', product_count: 12, aliases: [] }

const LISTADO = { items: [UN_RUBRO], unclassified_count: 0, total_products: 12 }

const UNA_FORMA_ESCRITA: Case = {
  id: 55,
  kind: 'unknown_category',
  reason: 'Una forma escrita de categoría que el sistema no conoce',
  payload: { category_text: 'Bulones Varios', products: 12, origin: 'Lista de precios' },
  section: 'PURCHASING',
  status: 'PENDING',
  batch_id: 4,
  occurrences: 1,
  decision: null,
  resolved_by_user_id: null,
  resolved_by_name: null,
  resolved_at: null,
  created_at: '2026-08-31T10:00:00Z',
  waiting_days: 0,
  is_stale: false,
} as unknown as Case

function secciones() {
  return within(screen.getByRole('navigation'))
    .getAllByRole('link')
    .map(link => link.textContent)
}

describe('los rubros en la barra lateral', () => {
  it('le aparecen a compras, que es quien los mantiene', () => {
    render(<Navigation user={USER} permissions={COMPRAS} />)

    // RF-09: entre las secciones a las que entra, sin que ninguna pantalla
    // sepa qué es un rol — la entrada declara `PRODUCT_CATEGORIES` y nada más.
    expect(secciones()).toContain('Rubros')
  })

  it('le siguen apareciendo a ventas, que los consulta', () => {
    render(<Navigation user={USER} permissions={VENTAS} />)

    // RF-10, y el que se rompe sin ruido: con `READ` hay que poder entrar. Si
    // la entrada exigiera edición, Julián tendría el permiso y ninguna puerta.
    expect(secciones()).toContain('Rubros')
  })
})

describe('las acciones sobre un rubro', () => {
  it('con el acceso de ventas la pantalla no ofrece ninguna', () => {
    render(<CategoryList listing={LISTADO} canEdit={canEdit(VENTAS, 'PRODUCT_CATEGORIES')} />)

    // RF-12: ni agregar, ni renombrar, ni eliminar. Lo que ve es el rubro.
    expect(screen.queryByRole('button')).toBeNull()
    expect(screen.getByText('Herramientas')).toBeInTheDocument()
  })

  it('con el acceso de compras están todas', () => {
    render(<CategoryList listing={LISTADO} canEdit={canEdit(COMPRAS, 'PRODUCT_CATEGORIES')} />)

    // RF-01, RF-02 y RF-03 del lado que se ve.
    for (const accion of ['Agregar', 'Renombrar', 'Eliminar']) {
      expect(screen.getByRole('button', { name: accion })).toBeInTheDocument()
    }
  })
})

describe('una forma escrita sin rubro, en la cola de revisión', () => {
  beforeEach(() => {
    vi.mocked(resolveCase).mockReset()
    vi.mocked(resolveCase).mockResolvedValue({ ok: true, data: UNA_FORMA_ESCRITA })
  })

  it('se dibuja con su nombre en castellano y con la forma que llegó', () => {
    render(<CaseCard item={UNA_FORMA_ESCRITA} mayCorrect={false} categories={[UN_RUBRO]} />)

    // Sin su entrada en `CASE_KINDS` la tarjeta escribe el `kind` crudo, en
    // inglés, en una pantalla que lee una persona (Artículo VIII).
    expect(screen.getByText('Forma escrita sin rubro')).toBeInTheDocument()
    expect(screen.getByText('Bulones Varios')).toBeInTheDocument()
  })

  it('la resuelve compras eligiendo un rubro, sin salir de la pantalla', async () => {
    const persona = userEvent.setup()
    render(<CaseCard item={UNA_FORMA_ESCRITA} mayCorrect={false} categories={[UN_RUBRO]} />)

    // Act — Marcela elige el rubro y la asigna, que es RF-14 entero: el mismo
    // lugar donde ya resuelve todo lo que la actualización aparta.
    await persona.selectOptions(screen.getByRole('combobox'), '3')
    await persona.click(screen.getByRole('button', { name: 'Asignar este rubro' }))

    // Assert — la decisión viaja como `category_id`, que es lo que el backend
    // espera para aprender la equivalencia y aplicarla hacia atrás (RF-06).
    expect(resolveCase).toHaveBeenCalledWith(55, { category_id: 3 })
  })

  it('no ofrece asignar hasta que hay un rubro elegido', () => {
    render(<CaseCard item={UNA_FORMA_ESCRITA} mayCorrect={false} categories={[UN_RUBRO]} />)

    // Resolver sin decisión es cerrar el caso sin decidirlo, que es lo que el
    // Artículo II no quiere: la cola existe para que alguien conteste.
    expect(screen.getByRole('button', { name: 'Asignar este rubro' })).toBeDisabled()
  })
})
