/**
 * RF-05: se pasa al mes siguiente y al anterior desde el propio calendario.
 *
 * Lo que se fija acá es que la ventana se calcula sobre la que el backend
 * devolvió —y no sobre la fecha de hoy— y que los filtros puestos sobreviven al
 * cambio de mes: cambiar de mes con «sólo sin recibo» activo y perder el filtro
 * es la forma silenciosa de mostrar de más.
 */
import { describe, expect, it } from 'vitest'

import { dayNumber, isInWindow, weeksOf, windowFor } from '@/lib/purchases/calendar'

/** Los parámetros de una URL de `/calendario`, para poder afirmar sobre ellos. */
function paramsOf(url: string): URLSearchParams {
  return new URLSearchParams(url.split('?')[1])
}

describe('el control de mes', () => {
  it('el mes siguiente es el mes entero que sigue a la ventana mirada', () => {
    const params = paramsOf(windowFor('2026-03-01', 1, {}))

    expect(params.get('since')).toBe('2026-04-01')
    expect(params.get('until')).toBe('2026-04-30')
  })

  it('el mes anterior es el mes entero que precede a la ventana mirada', () => {
    const params = paramsOf(windowFor('2026-03-01', -1, {}))

    expect(params.get('since')).toBe('2026-02-01')
    expect(params.get('until')).toBe('2026-02-28')
  })

  it('se calcula sobre la ventana mirada y no sobre el día en que empieza', () => {
    // Una ventana de dos semanas a mitad de mes: el «mes siguiente» sigue
    // siendo un mes entero, el que sigue al mes que se está mirando.
    const params = paramsOf(windowFor('2026-03-18', 1, {}))

    expect(params.get('since')).toBe('2026-04-01')
    expect(params.get('until')).toBe('2026-04-30')
  })

  it('cruza el fin de año en las dos direcciones', () => {
    expect(paramsOf(windowFor('2026-12-01', 1, {})).get('since')).toBe('2027-01-01')
    expect(paramsOf(windowFor('2026-01-01', -1, {})).get('until')).toBe('2025-12-31')
  })

  it('conserva los filtros puestos', () => {
    const params = paramsOf(windowFor('2026-03-01', 1, { sin_recibo: '1', saldadas: 'no' }))

    expect(params.get('sin_recibo')).toBe('1')
    expect(params.get('saldadas')).toBe('no')
  })

  it('no inventa filtros que nadie puso', () => {
    const params = paramsOf(windowFor('2026-03-01', 1, {}))

    expect(params.has('sin_recibo')).toBe(false)
    expect(params.has('saldadas')).toBe(false)
  })
})

describe('la grilla del mes', () => {
  it('cubre el mes entero en semanas de lunes a domingo', () => {
    const semanas = weeksOf('2026-03-01', '2026-03-31')

    expect(semanas.every(semana => semana.length === 7)).toBe(true)
    // Marzo de 2026 empieza domingo: la grilla arranca el lunes anterior.
    expect(semanas[0][0]).toBe('2026-02-23')
    expect(semanas.at(-1)?.at(-1)).toBe('2026-04-05')
  })

  it('un día sin vencimientos existe igual, que es lo que la lista no podía mostrar', () => {
    const dias = weeksOf('2026-03-01', '2026-03-31').flat()

    expect(dias).toHaveLength(6 * 7)
    // Los 31 días de marzo, sin agujeros: es la diferencia entre un calendario
    // y una lista de los días que tienen algo.
    for (let numero = 1; numero <= 31; numero += 1) {
      expect(dias).toContain(`2026-03-${String(numero).padStart(2, '0')}`)
    }
  })

  it('los días de relleno se distinguen de los de la ventana', () => {
    expect(isInWindow('2026-02-23', '2026-03-01', '2026-03-31')).toBe(false)
    expect(isInWindow('2026-03-01', '2026-03-01', '2026-03-31')).toBe(true)
    expect(isInWindow('2026-03-31', '2026-03-01', '2026-03-31')).toBe(true)
    expect(isInWindow('2026-04-05', '2026-03-01', '2026-03-31')).toBe(false)
  })

  it('no se corre de día según el huso del navegador', () => {
    // Una ventana que empieza un lunes se queda en ese lunes: con aritmética
    // local en vez de UTC, al oeste de Greenwich la grilla arrancaba el domingo.
    expect(weeksOf('2026-06-01', '2026-06-30')[0][0]).toBe('2026-06-01')
    expect(dayNumber('2026-06-01')).toBe('1')
    expect(dayNumber('2026-06-30')).toBe('30')
  })
})
