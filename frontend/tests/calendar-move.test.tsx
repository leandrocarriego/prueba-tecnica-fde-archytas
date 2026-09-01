/**
 * Mover un vencimiento: el guard de `busy`, y cómo se reconoce RF-25.
 *
 * Los dos son arreglos del review de la 006, y los dos son invisibles a ojo:
 *
 * **RF-25** — la pregunta «la fecha nueva ya pasó, ¿la movés igual?» se dispara
 * por un **código** en `details`, no por el texto del mensaje. Antes se
 * comparaba el castellano (`message.includes('ya pasó')`), y eso hacía de la
 * redacción de `MOVING_INTO_THE_PAST` un contrato que nadie declaró: cambiarle
 * una palabra al mensaje mataba la confirmación en silencio y convertía un
 * movimiento legítimo en un error. Este test es lo que avisa si vuelve a pasar.
 *
 * **El guard** — el primer intento de mover no pasaba por `busy`, así que el
 * botón seguía habilitado y la tarjeta arrastrable durante todo el viaje.
 *
 * **La pregunta es un diálogo de la aplicación**, no el `window.confirm` del
 * navegador. Eso la vuelve testeable como lo que es —algo que se ve y se
 * contesta— en vez de espiando una función global; y de paso deja fijado lo que
 * más se rompe de una confirmación: que cerrarla por `Escape` cuente como «sí».
 */
import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { moveDueDate } from '@/app/actions/purchases'
import { CalendarGrid } from '@/components/purchases/CalendarGrid'
import { MOVING_INTO_THE_PAST } from '@/lib/purchases/calendar'
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

const mover = vi.mocked(moveDueDate)

const CALENDAR = {
  since: '2026-03-01',
  until: '2026-03-31',
  items: [
    {
      id: 7,
      on_date: '2026-03-10',
      original_date: '2026-03-10',
      description: 'Alquiler',
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
    } as unknown as DueDate,
  ],
} as unknown as Calendar

/** Abre el panel de mover de la primera tarjeta y pide la fecha nueva. */
async function pedirMover(fecha: string) {
  const user = userEvent.setup()
  render(<CalendarGrid calendar={CALENDAR} canEdit />)
  await user.click(screen.getAllByRole('button', { name: 'Mover' })[0])

  const input = screen.getAllByLabelText('Fecha nueva')[0]
  fireEvent.change(input, { target: { value: fecha } })
  // `act` porque el handler es asíncrono: sin esto la aserción corre entre el
  // `setBusy(true)` y la respuesta, y React avisa que el árbol se movió solo.
  await act(async () => {
    fireEvent.submit(input.closest('form') as HTMLFormElement)
  })
  return user
}

beforeEach(() => {
  mover.mockReset()
})

describe('mover un vencimiento al pasado (RF-25)', () => {
  /** El diálogo que pregunta, si está abierto. */
  function pregunta() {
    return screen.queryByRole('dialog')
  }

  it('la pregunta la dispara el código de la negativa, no el texto del mensaje', async () => {
    // El mensaje dice algo **distinto** de «ya pasó» a propósito: si la pantalla
    // volviera a mirar el texto, este test falla y ahí está el punto.
    mover.mockResolvedValueOnce({
      ok: false,
      message: 'Otra redacción cualquiera',
      details: { code: MOVING_INTO_THE_PAST },
    })

    await pedirMover('2020-01-15')

    expect(pregunta()).toBeInTheDocument()
    // Y pregunta por **este** vencimiento y **esta** fecha, no en abstracto:
    // es el dato sobre el que se está decidiendo.
    expect(pregunta()).toHaveTextContent('Alquiler')
    expect(pregunta()).toHaveTextContent('15/01/2020')
  })

  it('decir que sí la repite con la confirmación puesta', async () => {
    mover.mockResolvedValueOnce({
      ok: false,
      message: 'La fecha nueva ya pasó',
      details: { code: MOVING_INTO_THE_PAST },
    })
    mover.mockResolvedValueOnce({ ok: true, data: CALENDAR.items[0] })
    const user = await pedirMover('2020-01-15')

    await user.click(screen.getByRole('button', { name: 'Moverlo igual' }))

    expect(mover).toHaveBeenNthCalledWith(2, 7, '2020-01-15', null, true)
    expect(pregunta()).not.toBeInTheDocument()
  })

  it('decir que no deja todo como estaba', async () => {
    mover.mockResolvedValueOnce({
      ok: false,
      message: 'La fecha nueva ya pasó',
      details: { code: MOVING_INTO_THE_PAST },
    })
    const user = await pedirMover('2020-01-15')

    await user.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(mover).toHaveBeenCalledOnce()
    expect(pregunta()).not.toBeInTheDocument()
  })

  it('cerrar el diálogo es decir que no, no seguir adelante', async () => {
    /*
     * Lo que más se rompe de un diálogo de confirmación: que salir por la puerta
     * de al lado —`Escape`, el fondo, la cruz— cuente como «sí». Acá `Escape`
     * tiene que dejar la factura donde estaba.
     */
    mover.mockResolvedValueOnce({
      ok: false,
      message: 'La fecha nueva ya pasó',
      details: { code: MOVING_INTO_THE_PAST },
    })
    const user = await pedirMover('2020-01-15')

    await user.keyboard('{Escape}')

    expect(mover).toHaveBeenCalledOnce()
    expect(pregunta()).not.toBeInTheDocument()
  })

  it('una negativa sin código se muestra como error, sin preguntar nada', async () => {
    mover.mockResolvedValueOnce({ ok: false, message: 'Ese vencimiento no existe' })

    await pedirMover('2026-03-20')

    expect(pregunta()).not.toBeInTheDocument()
    expect(await screen.findByText('Ese vencimiento no existe')).toBeInTheDocument()
  })
})

describe('mientras la escritura viaja', () => {
  it('lo dice, y no deja mandar la misma dos veces', async () => {
    // Una promesa que no se resuelve: la pantalla queda en el medio del viaje,
    // que es exactamente el momento que antes no se manejaba.
    mover.mockReturnValue(new Promise(() => {}))
    const user = await pedirMover('2026-03-20')

    expect(await screen.findByRole('status')).toHaveTextContent('Guardando…')

    // Pedirlo de nuevo no manda una segunda vez (`TS-08`, y el doble `PUT`).
    await act(async () => {
      fireEvent.submit(
        screen.getAllByLabelText('Fecha nueva')[0].closest('form') as HTMLFormElement
      )
    })
    expect(mover).toHaveBeenCalledOnce()

    // Y la tarjeta deja de ser arrastrable mientras tanto.
    expect(
      screen.getAllByRole('listitem').some(li => li.getAttribute('draggable') === 'true')
    ).toBe(false)
    void user
  })
})
