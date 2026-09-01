'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'

import { Input } from '@/components/ui/input'

/** Cuánto se espera a que la persona deje de tipear antes de buscar. */
const SEARCH_DEBOUNCE_MS = 300

interface RubroOption {
  id: number
  name: string
}

interface PriceFiltersProps {
  categories: RubroOption[]
  q: string
  changed: boolean
  categoryId: number | null
}

/**
 * La barra de filtros de la lista de precios (guía visual `3k`): buscar,
 * acotar por rubro y «sólo con cambios».
 *
 * Cada control es real y viaja en la URL, que es lo que hace que el server
 * component de la página vuelva a pedir la página filtrada: la búsqueda es el
 * parámetro `q`, el rubro es `rubro` (el `category_id` del backend) y «sólo con
 * cambios» es `changed`, el filtro que trae las filas cuyo precio se movió del
 * anterior. Ninguno es un botón de adorno.
 *
 * No es un naranja: filtrar es navegación, no la decisión de la pantalla. El
 * único acento se gasta abajo, en unificar rubros.
 *
 * La búsqueda es **en vivo**: filtra mientras se tipea, con un respiro de
 * {@link SEARCH_DEBOUNCE_MS} ms para no pedir una página por tecla. El Enter
 * sigue andando —dispara la misma búsqueda sin esperar—, pero no hace falta.
 */
export function PriceFilters({ categories, q, changed, categoryId }: PriceFiltersProps) {
  const router = useRouter()
  const [text, setText] = useState(q)

  function urlFor(nextText: string): string {
    const params = new URLSearchParams()
    if (nextText.trim()) params.set('q', nextText.trim())
    if (categoryId !== null) params.set('rubro', String(categoryId))
    if (changed) params.set('changed', '1')
    const query = params.toString()
    return query ? `/precios?${query}` : '/precios'
  }

  function go(overrides: Record<string, string | null>) {
    const params = new URLSearchParams()
    const next = {
      q: text.trim() || null,
      rubro: categoryId === null ? null : String(categoryId),
      changed: changed ? '1' : null,
      ...overrides,
    }
    for (const [key, value] of Object.entries(next)) {
      if (value) params.set(key, value)
    }
    const query = params.toString()
    router.push(query ? `/precios?${query}` : '/precios')
  }

  // Buscar en vivo: cada cambio del texto se agenda, y el anterior se cancela,
  // así sólo viaja la última pulsación. No corre en el primer render —el texto
  // ya viene de la URL— para no empujar una navegación redundante al abrir.
  const mounted = useRef(false)
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true
      return
    }
    const timer = setTimeout(() => router.push(urlFor(text)), SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text])

  const active = categoryId !== null

  return (
    <div className="flex flex-wrap items-center gap-2.5 border-b border-border px-4 py-3">
      <form
        className="min-w-0 flex-1"
        onSubmit={event => {
          event.preventDefault()
          go({ q: text.trim() || null })
        }}
      >
        <Input
          aria-label="Buscar producto o código"
          className="h-9 rounded-lg border-border bg-background"
          placeholder="Buscar producto o código…"
          value={text}
          onChange={event => setText(event.target.value)}
        />
      </form>

      {/*
        «Todos los rubros» es una píldora, como en el diseño: un `select` nativo
        —el control que el navegador dibuja mejor y el único cómodo en un
        teléfono— vestido de píldora. `appearance-none` le saca la flecha del
        sistema y le ponemos una discreta, para que se lea igual pero siga
        avisando que se despliega.
      */}
      <div className="relative flex-none">
        <select
          aria-label="Filtrar por rubro"
          className={`h-9 appearance-none rounded-full border py-1.5 pl-3.5 pr-8 text-xs font-medium ${
            active
              ? 'border-warn-border bg-warn-surface font-semibold text-warn'
              : 'border-input bg-card text-muted-foreground hover:bg-muted'
          }`}
          value={categoryId === null ? '' : String(categoryId)}
          onChange={event => go({ rubro: event.target.value || null })}
        >
          <option value="">Todos los rubros</option>
          {categories.map(category => (
            <option key={category.id} value={String(category.id)}>
              {category.name}
            </option>
          ))}
        </select>
        <span
          aria-hidden
          className={`pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[9px] ${
            active ? 'text-warn' : 'text-muted-ink'
          }`}
        >
          ▾
        </span>
      </div>

      <button
        type="button"
        aria-pressed={changed}
        onClick={() => go({ changed: changed ? null : '1' })}
        className={`flex-none rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
          changed
            ? 'border-warn-border bg-warn-surface text-warn'
            : 'border-input bg-card text-muted-foreground hover:bg-muted'
        }`}
      >
        Sólo con cambios
      </button>
    </div>
  )
}
