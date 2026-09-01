/**
 * El corte de compras del tablero, y lo que pasa cuando no está.
 *
 * Dos afirmaciones, y la segunda es la que se rompe sola. La primera: las tres
 * tarjetas de la guía visual (`3b`) dicen lo que contestó la API, y la lista de
 * vencimientos muestra el **saldo** y no el total —la diferencia entre decirle a
 * alguien lo que debe y decirle que pague de nuevo lo que ya pagó a medias—.
 *
 * La segunda: `/dashboard/purchases` pide `DASHBOARD` **y**
 * `PURCHASE_INVOICES`, así que a quien vende le contesta 403 y llega acá como
 * `null`. El tablero tiene que seguir siendo el tablero: la facturación en su
 * lugar y ni una tarjeta de compras vacía. Es la clase de defecto que nadie ve
 * hasta que entra la persona equivocada, porque con el acceso del dueño la
 * pantalla se ve perfecta.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import DashboardPage from '@/app/(private)/tablero/page'
import type { PurchasesDashboard } from '@/lib/purchases/types'
import type { SalesDashboard } from '@/lib/sales/types'

const fetchFromApi = vi.fn()
vi.mock('@/lib/api/server', () => ({ fetchFromApi: (path: string) => fetchFromApi(path) }))
vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh: vi.fn() }) }))

const SALES: SalesDashboard = {
  since: null,
  until: null,
  invoiced: { value: '1000000', sales: 10, excluded: 0, merged: 0, has_estimates: false },
  by_month: [],
  held_total: 0,
  pending_groups: 0,
} as SalesDashboard

const PURCHASES: PurchasesDashboard = {
  owed: '2147900',
  open_invoices: 14,
  excluded_in_review: 2,
  excluded_inconsistent: 0,
  due_soon_days: 7,
  due_soon: 6,
  due_soon_without_receipt: 3,
  overdue: 1,
  orders_pending: 4,
  orders_stalled: 2,
  stalled_days: 15,
  upcoming: [
    {
      invoice_id: 1,
      number: 'FC-1051',
      supplier_name: 'Ferrum Andina S.A.',
      supplier_text: 'FERRUM ANDINA',
      total: '486200',
      balance: '386200',
      due_on: '2026-09-03',
      days_left: 2,
      receipt_issued: false,
      in_review: false,
    },
    {
      invoice_id: 2,
      number: 'FC-1060',
      supplier_name: null,
      supplier_text: 'INSUMOS DEL VALLE',
      total: '212750',
      balance: '212750',
      due_on: '2026-09-07',
      days_left: 6,
      receipt_issued: true,
      in_review: true,
    },
  ],
} as PurchasesDashboard

/** La API contesta el corte de ventas siempre, y el de compras si se lo permite. */
function answerWith(purchases: PurchasesDashboard | null) {
  fetchFromApi.mockReset()
  fetchFromApi.mockImplementation((path: string) => {
    if (path.startsWith('/dashboard/sales')) return Promise.resolve(SALES)
    if (path.startsWith('/dashboard/purchases')) return Promise.resolve(purchases)
    return Promise.resolve(null)
  })
}

describe('el corte de compras del tablero', () => {
  it('dibuja las tres tarjetas con lo que contestó la API', async () => {
    answerWith(PURCHASES)
    render(await DashboardPage({ searchParams: Promise.resolve({}) }))

    expect(screen.getByText('$ 2.147.900')).toBeInTheDocument()
    expect(screen.getByText(/14 facturas abiertas/)).toBeInTheDocument()
    // El rótulo lleva el número de días que decidió el backend, no uno escrito
    // en la pantalla: si el corte cambia, el rótulo cambia con él.
    expect(screen.getByText('Vence en 7 días')).toBeInTheDocument()
    expect(screen.getByText(/3 sin recibo/)).toBeInTheDocument()
    // Y el límite de días parada sale del parámetro que configuró el dueño.
    expect(screen.getByText(/2 con más de 15 días/)).toBeInTheDocument()
  })

  it('dice lo que la deuda deja afuera, pegado a la deuda', async () => {
    answerWith(PURCHASES)
    render(await DashboardPage({ searchParams: Promise.resolve({}) }))

    expect(screen.getByText(/2 sin sumar \(2 en revisión\)/)).toBeInTheDocument()
  })

  it('en los vencimientos muestra el saldo, no el total de la factura', async () => {
    answerWith(PURCHASES)
    render(await DashboardPage({ searchParams: Promise.resolve({}) }))

    expect(screen.getByText('$ 386.200')).toBeInTheDocument()
    expect(screen.queryByText('$ 486.200')).toBeNull()
  })

  it('marca como sin confirmar la factura que nadie pudo atribuir', async () => {
    answerWith(PURCHASES)
    render(await DashboardPage({ searchParams: Promise.resolve({}) }))

    // Aparece igual —la fecha llega aunque nadie haya resuelto el proveedor— y
    // aparece marcada: su importe todavía no lo confirmó nadie.
    expect(screen.getByText('INSUMOS DEL VALLE')).toBeInTheDocument()
    expect(screen.getByText('Sin confirmar')).toBeInTheDocument()
  })

  it('sin permiso sobre compras, el tablero sigue siendo el tablero', async () => {
    answerWith(null)
    render(await DashboardPage({ searchParams: Promise.resolve({}) }))

    expect(screen.getByText('$ 1.000.000')).toBeInTheDocument()
    expect(screen.queryByText('Deuda a proveedores')).toBeNull()
    expect(screen.queryByText('Próximos vencimientos')).toBeNull()
  })
})
