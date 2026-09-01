'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'

import { Input } from '@/components/ui/input'

/** Cuánto se espera a que la persona deje de tipear antes de filtrar. */
const SEARCH_DEBOUNCE_MS = 300

/** Los tres cortes del padrón, como los dibuja la guía (`3n`). */
export const SUPPLIER_VIEWS = {
  todos: 'Todos',
  deuda: 'Con deuda',
  revisar: 'A revisar',
} as const

export type SupplierView = keyof typeof SUPPLIER_VIEWS

/**
 * La barra de filtros del padrón (guía visual `3n`): buscar y acotar por corte.
 *
 * Igual que la de precios, y a propósito: los dos son padrones y el que pasa de
 * uno al otro tiene que encontrar el mismo control en el mismo lugar. La
 * búsqueda es en vivo, con un respiro para no navegar por tecla, y todo viaja en
 * la URL — lo que se está mirando se puede compartir y el navegador lo recuerda.
 *
 * **«A revisar» lleva su cuenta encendida y las otras no.** Es el corte que
 * espera trabajo de una persona, y un número al lado es la diferencia entre un
 * filtro y un aviso. En cero no se pinta: un ámbar que dice «0» enseña que el
 * color no quiere decir nada.
 */
export function SupplierFilters({
  q,
  view,
  toReview,
}: {
  q: string
  view: SupplierView
  toReview: number
}) {
  const router = useRouter()
  const [text, setText] = useState(q)

  function urlFor(nextText: string, nextView: SupplierView): string {
    const params = new URLSearchParams()
    if (nextText.trim()) params.set('q', nextText.trim())
    if (nextView !== 'todos') params.set('ver', nextView)
    const query = params.toString()
    return query ? `/proveedores?${query}` : '/proveedores'
  }

  // No corre en el primer render: el texto ya viene de la URL, y navegar al
  // abrir sería un viaje por algo que la pantalla ya tiene.
  const mounted = useRef(false)
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true
      return
    }
    const timer = setTimeout(() => router.push(urlFor(text, view)), SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text])

  return (
    <div className="flex flex-wrap items-center gap-2.5 border-b border-border px-4 py-3">
      <form
        className="min-w-0 flex-1"
        onSubmit={event => {
          event.preventDefault()
          router.push(urlFor(text, view))
        }}
      >
        <Input
          aria-label="Buscar por nombre o CUIT"
          className="h-9 rounded-lg border-border bg-background"
          placeholder="Buscar por nombre o CUIT…"
          value={text}
          onChange={event => setText(event.target.value)}
        />
      </form>

      {(Object.keys(SUPPLIER_VIEWS) as SupplierView[]).map(id => {
        const current = id === view
        const alerting = id === 'revisar' && toReview > 0
        return (
          <button
            key={id}
            type="button"
            aria-pressed={current}
            onClick={() => router.push(urlFor(text, id))}
            className={`flex-none cursor-pointer rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
              current
                ? 'border-primary bg-primary text-primary-foreground'
                : alerting
                  ? 'border-warn-border bg-warn-surface text-warn'
                  : 'border-input bg-card text-muted-foreground hover:bg-muted'
            }`}
          >
            {SUPPLIER_VIEWS[id]}
            {id === 'revisar' && toReview > 0 && ` (${toReview})`}
          </button>
        )
      })}
    </div>
  )
}
