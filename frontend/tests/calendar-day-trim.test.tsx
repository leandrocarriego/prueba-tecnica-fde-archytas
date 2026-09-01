/**
 * RF-01 y RF-08: la grilla del mes, y el recorte por día.
 *
 * **RF-08** — un día con ocho vencimientos indica que hay ocho y permite verlos
 * todos. El recorte existe para que un día cargado no empuje los demás fuera de
 * la pantalla, que es lo que un calendario tiene que evitar por definición. No
 * hay forma de verificarlo desde el backend: el backend devuelve los ocho.
 *
 * **RF-01** — la pantalla es un calendario y no una lista de los días que
 * tienen algo: un día sin vencimientos aparece igual, vacío. Acá se fija sobre
 * el componente montado; la aritmética de las semanas está en
 * `calendar-month-control.test.ts`.
 *
 * Se monta el componente real. Lo único que se reemplaza es lo que sale de la
 * pantalla —las server actions, el router y el canal en vivo—, porque nada de
 * eso participa de lo que se prueba.
 *
 * **Las dos vistas se dibujan a la vez** y el CSS decide cuál se ve: la grilla
 * desde `md`, la lista de días en un teléfono (RF-41). `jsdom` no aplica CSS,
 * así que cada aserción dice explícitamente en cuál de las dos mira.
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { CalendarGrid } from '@/components/purchases/CalendarGrid'
import type { Calendar, DueDate } from '@/lib/purchases/types'

vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh: vi.fn() }) }))
vi.mock('@/app/actions/purchases', () => ({
  addDueDate: vi.fn(),
  editDueDate: vi.fn(),
  moveDueDate: vi.fn(),
  removeDueDate: vi.fn(),
}))
vi.mock('@/components/purchases/useLiveCalendar', () => ({
  useLiveCalendar: () => ({ state: 'en-vivo', lastChange: null, viewers: [] }),
}))

const DAY = '2026-03-10'

/** Una tarjeta del calendario, con lo mínimo que la pantalla lee de ella. */
function entry(id: number, on_date = DAY, overrides: Partial<DueDate> = {}): DueDate {
  return {
    id,
    on_date,
    original_date: on_date,
    description: `Vencimiento ${id}`,
    amount: '1000',
    origin: 'MANUAL',
    invoice_id: null,
    supplier_name: null,
    is_past: false,
    was_rescheduled: false,
    receipt_issued: false,
    is_overdue_without_receipt: false,
    payment_state: null,
    created_by_user_id: null,
    created_by_name: null,
    created_at: null,
    changes: [],
    ...overrides,
  } as unknown as DueDate
}

/** Una ventana de marzo con `count` vencimientos el mismo día. */
function calendarWith(count: number, on_date = DAY): Calendar {
  return {
    since: '2026-03-01',
    until: '2026-03-31',
    items: Array.from({ length: count }, (_, index) => entry(index + 1, on_date)),
  } as unknown as Calendar
}

/** La lista de días, que es lo que se lee en un teléfono. */
function lista() {
  return within(screen.getByRole('list', { name: 'Los días con vencimientos' }))
}

/** La grilla del mes, que es lo que se lee en una pantalla ancha. */
function grilla() {
  return within(screen.getByRole('list', { name: 'El mes, día por día' }))
}

describe('el recorte por día', () => {
  it('un día con ocho muestra cuatro y dice que hay cuatro más', () => {
    render(<CalendarGrid calendar={calendarWith(8)} canEdit />)

    expect(lista().getAllByText(/^Vencimiento \d+$/)).toHaveLength(4)
    expect(lista().getByRole('button', { name: 'y 4 más en este día' })).toBeInTheDocument()
  })

  it('pedirlo abre el día entero, y volver a pedirlo lo cierra', async () => {
    const user = userEvent.setup()
    render(<CalendarGrid calendar={calendarWith(8)} canEdit />)

    await user.click(lista().getByRole('button', { name: 'y 4 más en este día' }))
    expect(lista().getAllByText(/^Vencimiento \d+$/)).toHaveLength(8)

    await user.click(lista().getByRole('button', { name: 'Ver menos' }))
    expect(lista().getAllByText(/^Vencimiento \d+$/)).toHaveLength(4)
  })

  it('un día que entra entero no recorta ni ofrece verlo', () => {
    render(<CalendarGrid calendar={calendarWith(4)} canEdit />)

    expect(lista().getAllByText(/^Vencimiento \d+$/)).toHaveLength(4)
    expect(lista().queryByText(/más en este día/)).not.toBeInTheDocument()
  })

  it('el recorte es de cada día, no de la pantalla', () => {
    // Cinco el 10 y cinco el 11: cada día recorta por su cuenta, y ninguno
    // empuja al otro fuera de la vista.
    const calendar = {
      ...calendarWith(5),
      items: [...calendarWith(5, '2026-03-10').items, ...calendarWith(5, '2026-03-11').items],
    } as Calendar
    render(<CalendarGrid calendar={calendar} canEdit />)

    expect(lista().getAllByText(/^Vencimiento \d+$/)).toHaveLength(8)
    expect(lista().getAllByRole('button', { name: 'y 1 más en este día' })).toHaveLength(2)
  })

  it('la celda del día también recorta, y dice cuántos quedan', () => {
    render(<CalendarGrid calendar={calendarWith(8)} canEdit />)

    // La celda se busca por su nombre accesible —la fecha y cuántos vencen—,
    // que es lo que un lector de pantalla anuncia. Antes se la buscaba por el
    // texto de las tarjetas de adentro, que nombraba la celda con las cuatro
    // descripciones pegadas: lo que se recorta no puede ser también la etiqueta
    // de lo que recorta.
    const celda = grilla().getByRole('button', { name: '10/03/2026, 8 vencimientos' })
    expect(within(celda).getAllByText(/^Vencimiento \d+$/)).toHaveLength(4)
    expect(within(celda).getByText('y 4 más')).toBeInTheDocument()
  })

  it('un día vacío dice que no vence nada, y se puede abrir igual', async () => {
    const user = userEvent.setup()
    render(<CalendarGrid calendar={calendarWith(8)} canEdit />)

    // RF-01: en un calendario, «acá no vence nada» también es información, y es
    // lo que una lista de los días con algo no puede mostrar.
    const vacio = grilla().getByRole('button', { name: '06/03/2026, no vence nada' })
    await user.click(vacio)

    expect(screen.getByText('No vence nada este día.')).toBeInTheDocument()
    expect(vacio).toHaveAttribute('aria-current', 'date')
  })
})

describe('la grilla del mes', () => {
  it('tiene una celda por día, también los días en que no vence nada', () => {
    render(<CalendarGrid calendar={calendarWith(1)} canEdit />)

    // Marzo de 2026 entra en seis semanas de lunes a domingo: 42 celdas, y no
    // una fila por cada día que tenga algo.
    expect(grilla().getAllByRole('listitem')).toHaveLength(42)
    expect(grilla().getByText('31')).toBeInTheDocument()
  })

  it('el día abierto es el que tiene algo, y muestra su tarjeta entera', () => {
    render(<CalendarGrid calendar={calendarWith(1)} canEdit />)

    // La tarjeta entera aparece dos veces —una por vista— y las dos ofrecen
    // mover: es la misma tarjeta dibujada en los dos lugares.
    expect(screen.getAllByRole('button', { name: 'Mover' })).toHaveLength(2)
  })
})

describe('los estados de una tarjeta (`UI-03`)', () => {
  /** Una ventana con un solo vencimiento, en el estado que se pida. */
  function conEstado(overrides: Partial<DueDate>): Calendar {
    return {
      since: '2026-03-01',
      until: '2026-03-31',
      items: [entry(1, DAY, overrides)],
    } as unknown as Calendar
  }

  it('van en la píldora, y el estado de pago con su nombre y no con el enum', () => {
    render(<CalendarGrid calendar={conEstado({ payment_state: 'SIN_PAGOS' })} canEdit />)

    // Antes esto salía como «· sin_pagos», con guión bajo: el enum del backend
    // llegando crudo a la pantalla.
    expect(lista().getAllByText('Sin pagos')[0]).toBeInTheDocument()
    expect(lista().queryByText(/sin_pagos/i)).not.toBeInTheDocument()
  })

  it('lo que venció sin recibo tapa al recibo emitido: el color se gana', () => {
    render(
      <CalendarGrid
        calendar={conEstado({ is_overdue_without_receipt: true, receipt_issued: true })}
        canEdit
      />
    )

    expect(lista().getAllByText('Venció sin recibo')[0]).toBeInTheDocument()
    expect(lista().queryByText('Recibo emitido')).not.toBeInTheDocument()
  })

  it('«ya pasó» no se repite cuando ya hay una píldora roja diciendo más', () => {
    render(<CalendarGrid calendar={conEstado({ is_past: true })} canEdit />)
    expect(lista().getAllByText('Ya pasó')[0]).toBeInTheDocument()

    cleanup()
    render(
      <CalendarGrid
        calendar={conEstado({ is_past: true, is_overdue_without_receipt: true })}
        canEdit
      />
    )
    expect(lista().queryByText('Ya pasó')).not.toBeInTheDocument()
  })
})
