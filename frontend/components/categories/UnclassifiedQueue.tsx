'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { setProductCategory } from '@/app/actions/categories'
import { Button } from '@/components/ui/button'
import type { Category, UnclassifiedList } from '@/lib/catalog/types'

/**
 * The products waiting for a rubro, each with the proposal — or without one.
 *
 * Confirming the proposal and correcting it are **the same button plus the same
 * select**: only the rubro that travels differs (RF-15). A product with no
 * proposal is presented to classify without one (RF-17), because a subcategory
 * that points at two rubros is not "known", and breaking the tie would be the
 * system deciding.
 */
export function UnclassifiedQueue({
  queue,
  categories,
  canEdit,
}: {
  queue: UnclassifiedList
  categories: Category[]
  canEdit: boolean
}) {
  const router = useRouter()
  const [chosen, setChosen] = useState<Record<number, number>>({})
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function assign(productId: number, categoryId: number) {
    setBusy(true)
    setError(null)
    const result = await setProductCategory(productId, categoryId)
    setBusy(false)
    if (result.ok) {
      router.refresh()
      return
    }
    setError(result.message)
  }

  if (queue.items.length === 0) {
    return (
      <p className="rounded border border-dashed p-8 text-center text-muted-foreground">
        No quedó ningún producto sin rubro.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {error && (
        <p className="rounded border border-danger-border bg-danger-surface p-3 text-sm text-danger">
          {error}
        </p>
      )}

      {queue.items.map(item => {
        const selected = chosen[item.product_id] ?? item.proposed_category_id ?? 0
        return (
          <article key={item.product_id} className="space-y-2 rounded border p-4">
            <header className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="font-medium">
                {item.code} — {item.description}
              </h3>
              <p className="text-sm text-muted-foreground">
                {item.category_raw
                  ? `Llegó como «${item.category_raw}»`
                  : 'Llegó sin categoría cargada'}
                {item.subcategory_raw && ` · subcategoría: ${item.subcategory_raw}`}
              </p>
            </header>

            <p className="text-sm">
              {item.proposed_category_name ? (
                <>
                  El sistema propone <strong>{item.proposed_category_name}</strong>, por los
                  productos de esa subcategoría que ya están clasificados.
                </>
              ) : (
                'Sin propuesta: su subcategoría no resuelve a un solo rubro.'
              )}
            </p>

            {canEdit && (
              <div className="flex flex-wrap items-center gap-2">
                <select
                  className="rounded border px-2 py-1 text-sm"
                  value={selected}
                  onChange={event =>
                    setChosen({ ...chosen, [item.product_id]: Number(event.target.value) })
                  }
                >
                  <option value={0}>Elegí un rubro…</option>
                  {categories.map(category => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
                <Button
                  type="button"
                  disabled={busy || selected === 0}
                  onClick={() => void assign(item.product_id, selected)}
                >
                  {selected === item.proposed_category_id ? 'Confirmar' : 'Asignar'}
                </Button>
              </div>
            )}
          </article>
        )
      })}
    </div>
  )
}
