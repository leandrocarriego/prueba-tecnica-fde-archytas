'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

import { createCategory, deleteCategory, renameCategory } from '@/app/actions/categories'
import { count } from '@/lib/format'
import { isUnconfirmedCategoryAlias, pill } from '@/lib/ui/tone'
import type { CategoryList } from '@/lib/catalog/types'
import { Code, Money } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Notice } from '@/components/ui/notice'

interface RubroNormalizerProps {
  listing: CategoryList
  /** Whether this person may edit rubros (compras y el dueño), from the permission matrix. */
  canEdit: boolean
}

/**
 * «Rubros y sus formas escritas» (guía visual `3k`): el único panel de la
 * pantalla de Rubros, con el diseño acordado y las acciones reales adentro.
 *
 * A la izquierda cada rubro con cuántas formas llega escrito y cuántos productos
 * tiene; abajo, «Sin rubro» como un grupo más. A la derecha, el rubro elegido:
 * su nombre —que se cambia en el mismo lugar—, sus formas escritas, el impacto
 * de tocarlo y las acciones. Arriba a la derecha, el «+» para agregar uno.
 *
 * **Todo botón hace lo que dice, sin diálogos del navegador.** Agregar y
 * cambiar el nombre editan en línea: un `window.prompt` es un control que el
 * navegador puede suprimir de por vida con un tilde, y entonces «no anda». Se
 * escribe en un campo de la propia pantalla. Eliminar y «gestionar
 * equivalencias» son las otras dos acciones reales.
 *
 * **El gasto por rubro no está acá a propósito.** Es la otra mitad de P7 y quedó
 * fuera de las features 008 y 009: el origen no dice qué productos se compraron,
 * así que repartir un total entre rubros sería inventarlo (Art. II). Se agrega
 * cuando exista una fuente que ligue lo gastado con el producto.
 *
 * Las acciones se muestran según `canEdit`, que es una comodidad sobre el
 * backend —el que decide el 403—, no el mecanismo (010).
 */
export function RubroNormalizer({ listing, canEdit }: RubroNormalizerProps) {
  const router = useRouter()
  const rubros = listing.items
  const [selected, setSelected] = useState<number | 'unclassified'>(rubros[0]?.id ?? 'unclassified')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  // Alta en línea del rubro nuevo, disparada por el «+».
  const [adding, setAdding] = useState(false)
  const [addDraft, setAddDraft] = useState('')
  // Cambio de nombre en línea del rubro elegido.
  const [renaming, setRenaming] = useState(false)
  const [renameDraft, setRenameDraft] = useState('')

  const current = rubros.find(rubro => rubro.id === selected) ?? null

  async function run(action: () => Promise<{ ok: boolean; message?: string }>): Promise<boolean> {
    setBusy(true)
    setError(null)
    const result = await action()
    setBusy(false)
    if (result.ok) {
      router.refresh()
      return true
    }
    setError(result.message ?? 'No se pudo guardar')
    return false
  }

  function pick(next: number | 'unclassified') {
    setSelected(next)
    setRenaming(false)
  }

  async function submitAdd() {
    if (!addDraft.trim()) return
    if (await run(() => createCategory(addDraft.trim()))) {
      setAddDraft('')
      setAdding(false)
    }
  }

  async function submitRename() {
    const next = renameDraft.trim()
    if (!current || !next || next === current.name) {
      setRenaming(false)
      return
    }
    if (await run(() => renameCategory(current.id, next))) setRenaming(false)
  }

  return (
    <section className="rounded-xl border border-border bg-card p-6">
      {error && <Notice tone="danger" title={error} className="mb-4" />}

      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Rubros y sus formas escritas</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Cada rubro con todas las maneras en que llega escrito. La decisión y el nombre final los
            pone el usuario.
          </p>
        </div>

        {canEdit &&
          (adding ? (
            <form
              className="flex flex-none items-center gap-2"
              onSubmit={event => {
                event.preventDefault()
                void submitAdd()
              }}
            >
              <Input
                autoFocus
                aria-label="Nombre del rubro nuevo"
                placeholder="Nombre del rubro"
                value={addDraft}
                maxLength={100}
                disabled={busy}
                onChange={event => setAddDraft(event.target.value)}
                onKeyDown={event => {
                  if (event.key === 'Escape') setAdding(false)
                }}
                className="h-9 w-48"
              />
              <Button type="submit" variant="default" size="sm" disabled={busy || !addDraft.trim()}>
                Guardar
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={busy}
                onClick={() => setAdding(false)}
              >
                Cancelar
              </Button>
            </form>
          ) : (
            // El único naranja de la pantalla (`UI-05`): agregar un rubro es la
            // tarea. El «+» arriba a la derecha la abre.
            <Button
              variant="brand"
              size="icon"
              aria-label="Agregar rubro"
              title="Agregar rubro"
              disabled={busy}
              onClick={() => {
                setAddDraft('')
                setAdding(true)
              }}
              className="shrink-0 text-xl leading-none"
            >
              +
            </Button>
          ))}
      </div>

      <div className="mt-4 flex flex-col gap-4 md:flex-row md:items-stretch">
        <ul className="w-full flex-none divide-y divide-border overflow-hidden rounded-lg border border-border md:w-60">
          {rubros.map(rubro => (
            <li key={rubro.id}>
              <button
                type="button"
                onClick={() => pick(rubro.id)}
                className={`block w-full px-4 py-3 text-left hover:bg-muted ${
                  rubro.id === selected ? 'border-l-[3px] border-brand bg-background' : ''
                }`}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-semibold text-foreground">{rubro.name}</span>
                  <Money
                    value={rubro.spend}
                    as="span"
                    className="text-sm font-medium text-foreground"
                  />
                </div>
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
              onClick={() => pick('unclassified')}
              className={`block w-full px-4 py-3 text-left hover:bg-muted ${
                selected === 'unclassified' ? 'border-l-[3px] border-brand bg-background' : ''
              }`}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-sm font-semibold text-warn">Sin rubro</span>
                <Money value={listing.spend_unclassified} as="span" className="text-sm font-medium text-warn" />
              </div>
              <div className="mt-0.5 text-xs text-muted-foreground">
                {countLabel(listing.unclassified_count, 'producto', 'productos')}
              </div>
            </button>
          </li>
        </ul>

        <div className="min-w-0 flex-1">
          {selected === 'unclassified' ? (
            <UnclassifiedPanel
              count={listing.unclassified_count}
              pendingReview={listing.pending_review_count}
            />
          ) : current ? (
            <div className="flex h-full flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="text-sm text-muted-foreground">Se lee como</span>
                {renaming ? (
                  <form
                    className="flex items-center gap-2"
                    onSubmit={event => {
                      event.preventDefault()
                      void submitRename()
                    }}
                  >
                    <Input
                      autoFocus
                      aria-label="Nombre del rubro"
                      value={renameDraft}
                      maxLength={100}
                      disabled={busy}
                      onChange={event => setRenameDraft(event.target.value)}
                      onKeyDown={event => {
                        if (event.key === 'Escape') setRenaming(false)
                      }}
                      className="h-9 w-48"
                    />
                    <Button type="submit" variant="default" size="sm" disabled={busy}>
                      Guardar
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={busy}
                      onClick={() => setRenaming(false)}
                    >
                      Cancelar
                    </Button>
                  </form>
                ) : (
                  <>
                    <span className="inline-flex items-center rounded-md border border-input bg-card px-3 py-2 text-sm font-semibold text-foreground">
                      {current.name}
                    </span>
                    {canEdit && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          setRenameDraft(current.name)
                          setRenaming(true)
                        }}
                        className="text-xs font-medium text-link hover:underline disabled:opacity-50"
                      >
                        Cambiar nombre
                      </button>
                    )}
                  </>
                )}
              </div>

              <div className="flex items-baseline gap-2">
                <Money
                  value={current.spend}
                  as="span"
                  className="text-2xl font-semibold text-foreground"
                />
                <span className="text-sm text-muted-foreground">gastado en compras</span>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {current.aliases.length === 0 ? (
                  <span className="text-sm text-muted-foreground">
                    Todavía no llegó escrito de otra forma.
                  </span>
                ) : (
                  current.aliases.map(alias => (
                    <Badge
                      key={alias.id}
                      tone={pill('neutral', isUnconfirmedCategoryAlias(alias.source))}
                    >
                      <Code value={alias.text_original} />
                    </Badge>
                  ))
                )}
              </div>

              <div className="rounded-lg border border-border bg-muted p-4">
                <div className="text-sm font-semibold text-foreground">Impacto</div>
                <div className="mt-2.5 flex gap-6">
                  <Figure value={String(current.product_count)} label="productos" />
                  <Figure value={String(current.aliases.length)} label="formas escritas" />
                  <Figure value="Sí" label="se puede deshacer" tone="ok" />
                </div>
              </div>

              <div className="mt-auto flex flex-wrap items-center justify-end gap-2.5 pt-2">
                {canEdit && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busy || current.product_count > 0 || current.aliases.length > 0}
                    title={
                      current.product_count > 0 || current.aliases.length > 0
                        ? 'Tiene productos o formas escritas: primero reasignalos'
                        : undefined
                    }
                    onClick={() => void run(() => deleteCategory(current.id))}
                  >
                    Eliminar rubro
                  </Button>
                )}
                {/* Navegación, no un naranja: separar o repuntar una forma escrita
                    se hace en las equivalencias, donde esa decisión se guarda como
                    regla reutilizable (Art. II). */}
                <Button variant="default" size="sm" asChild>
                  <Link href="/rubros/equivalencias">Gestionar equivalencias</Link>
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Ese rubro ya no está. Elegí otro de la izquierda.
            </p>
          )}
        </div>
      </div>

      <p className="mt-4 text-sm text-muted-foreground">
        Gasto total en compras:{' '}
        <Money value={listing.spend_total} as="span" className="font-medium text-foreground" /> — de
        los cuales{' '}
        <Money value={listing.spend_unclassified} as="span" className="font-medium text-warn" />{' '}
        cayeron en «sin rubro». {count(listing.total_products)} productos en total: la suma de los
        rubros más «sin rubro» cierra el corte, sin pedazos sueltos.
      </p>
    </section>
  )
}

function UnclassifiedPanel({ count, pendingReview }: { count: number; pendingReview: number }) {
  return (
    <div className="flex h-full flex-col gap-3">
      <p className="text-sm text-foreground">
        {count === 0
          ? 'No hay productos esperando un rubro.'
          : `${countLabel(count, 'producto', 'productos')} todavía sin rubro. El sistema propone uno para cada uno; la última palabra es del usuario.`}
      </p>
      {pendingReview > 0 && (
        <p className="text-sm text-muted-foreground">
          {countLabel(pendingReview, 'forma escrita espera', 'formas escritas esperan')} una decisión
          en{' '}
          <Link className="text-link hover:underline" href="/revision">
            revisión
          </Link>
          .
        </p>
      )}
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
