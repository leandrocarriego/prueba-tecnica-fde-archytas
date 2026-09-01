'use client'

import Link from 'next/link'
import { useState } from 'react'

import type { CategoryList } from '@/lib/catalog/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface RubroNormalizerProps {
  listing: CategoryList
}

/**
 * «Rubros · sus formas escritas» (guía visual `3k`), con datos reales.
 *
 * A la izquierda cada rubro con cuántas formas llega escrito (sus grafías) y
 * cuántos productos tiene; abajo de todo, «Sin rubro» como un grupo más. A la
 * derecha, el rubro elegido con sus formas y el impacto de tocarlo.
 *
 * **Qué es y qué no es.** En el modelo actual las formas escritas ya están
 * resueltas a su rubro: no hay grafías «pendientes de unificar» flotando como
 * en el boceto. Por eso este panel es una **revisión** —muestra lo que ya está
 * agrupado— y el punto de entrada a donde esas decisiones se toman de verdad:
 * las equivalencias y la cola de sin rubro. No inventa un «aplicar» que el
 * backend no tiene, ni el conteo de facturas afectadas, que vive en otro módulo
 * y no se lee cruzando la frontera (Art. IV).
 */
export function RubroNormalizer({ listing }: RubroNormalizerProps) {
  const rubros = listing.items
  const [selected, setSelected] = useState<number | 'unclassified'>(rubros[0]?.id ?? 'unclassified')

  const current = rubros.find(rubro => rubro.id === selected) ?? null

  return (
    <section className="rounded-xl border border-border bg-card p-6">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Rubros y sus formas escritas</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Cada rubro con todas las maneras en que llega escrito. La decisión y el nombre final los
          pone el usuario.
        </p>
      </div>

      <div className="mt-4 flex flex-col gap-4 md:flex-row md:items-stretch">
        <ul className="w-full flex-none divide-y divide-border overflow-hidden rounded-lg border border-border md:w-60">
          {rubros.map(rubro => (
            <li key={rubro.id}>
              <button
                type="button"
                onClick={() => setSelected(rubro.id)}
                className={`block w-full px-4 py-3 text-left hover:bg-muted ${
                  rubro.id === selected ? 'border-l-[3px] border-brand bg-background' : ''
                }`}
              >
                <div className="text-sm font-semibold text-foreground">{rubro.name}</div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {countLabel(rubro.aliases.length, 'variante', 'variantes')} ·{' '}
                  {countLabel(rubro.product_count, 'producto', 'productos')}
                </div>
              </button>
            </li>
          ))}
          <li>
            <button
              type="button"
              onClick={() => setSelected('unclassified')}
              className={`block w-full px-4 py-3 text-left hover:bg-muted ${
                selected === 'unclassified' ? 'border-l-[3px] border-brand bg-background' : ''
              }`}
            >
              <div className="text-sm font-semibold text-warn">Sin rubro</div>
              <div className="mt-0.5 text-xs text-muted-foreground">
                {countLabel(listing.unclassified_count, 'producto', 'productos')}
              </div>
            </button>
          </li>
        </ul>

        <div className="min-w-0 flex-1">
          {selected === 'unclassified' ? (
            <UnclassifiedPanel count={listing.unclassified_count} />
          ) : current ? (
            <RubroPanel category={current} />
          ) : (
            <p className="text-sm text-muted-foreground">Todavía no hay rubros cargados.</p>
          )}
        </div>
      </div>
    </section>
  )
}

function RubroPanel({ category }: { category: CategoryList['items'][number] }) {
  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="text-sm text-muted-foreground">Se lee como</span>
        <span className="inline-flex items-center rounded-md border border-input bg-card px-3 py-2 text-sm font-semibold text-foreground">
          {category.name}
        </span>
        <Link className="text-xs font-medium text-link hover:underline" href="/rubros">
          Cambiar nombre
        </Link>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {category.aliases.length === 0 ? (
          <span className="text-sm text-muted-foreground">
            Todavía no llegó escrito de otra forma.
          </span>
        ) : (
          category.aliases.map(alias => (
            <Badge key={alias.id} tone="draft">
              {alias.text_original}
            </Badge>
          ))
        )}
      </div>

      <div className="rounded-lg border border-border bg-muted p-4">
        <div className="text-sm font-semibold text-foreground">Impacto</div>
        <div className="mt-2.5 flex gap-6">
          <Figure value={String(category.product_count)} label="productos" />
          <Figure value={String(category.aliases.length)} label="formas escritas" />
          <Figure value="Sí" label="se puede deshacer" tone="ok" />
        </div>
      </div>

      {/*
        Sin naranja. Este panel vive en la pantalla de Rubros, cuyo único acento
        (`UI-05`) se gasta en «Agregar rubro» del gestor de abajo. Acá los dos
        controles son navegación hacia donde la decisión se toma y se guarda como
        regla reutilizable (Art. II): tinta el principal, contorno el secundario.
      */}
      <div className="mt-auto flex flex-wrap justify-end gap-2.5 pt-2">
        <Button variant="outline" size="sm" asChild>
          <Link href="/rubros/equivalencias">Separar alguna</Link>
        </Button>
        <Button variant="default" size="sm" asChild>
          <Link href="/rubros/equivalencias">Gestionar equivalencias</Link>
        </Button>
      </div>
    </div>
  )
}

function UnclassifiedPanel({ count }: { count: number }) {
  return (
    <div className="flex h-full flex-col gap-3">
      <p className="text-sm text-foreground">
        {count === 0
          ? 'No hay productos esperando un rubro.'
          : `${countLabel(count, 'producto', 'productos')} todavía sin rubro. El sistema propone uno para cada uno; la última palabra es del usuario.`}
      </p>
      {/*
        Tinta, no naranja. El único acento de la pantalla se gasta en la
        decisión sobre las formas escritas de un rubro (`UI-05`); acá el enlace a
        asignar en lote es una acción más, y además ya vive en naranja-azul en la
        tarjeta «Nuevos sin rubro» de arriba.
      */}
      <div className="mt-auto flex justify-end pt-2">
        <Button variant="default" size="sm" asChild>
          <Link href="/rubros/sin-clasificar">Asignar en lote →</Link>
        </Button>
      </div>
    </div>
  )
}

function Figure({ value, label, tone }: { value: string; label: string; tone?: 'ok' }) {
  return (
    <div>
      <div className={`amount text-lg ${tone === 'ok' ? 'text-ok' : 'text-foreground'}`}>{value}</div>
      <div className="mt-1 text-xs text-muted-foreground">{label}</div>
    </div>
  )
}

function countLabel(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`
}
