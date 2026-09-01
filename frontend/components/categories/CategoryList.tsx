'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { createCategory, deleteCategory, renameCategory } from '@/app/actions/categories'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { count } from '@/lib/format'
import type { CategoryList as CategoryListRead } from '@/lib/catalog/types'
import { Notice } from '@/components/ui/notice'
import { Code } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { isUnconfirmedCategoryAlias, pill } from '@/lib/ui/tone'

/**
 * The rubros, with how many products each one has and how it arrives written.
 *
 * «Sin rubro» is shown as one more group, and it has no buttons: it is not a
 * row of the catalog, it is the products with no rubro (RF-09). That is why
 * the totals below add up without it being editable.
 */
export function CategoryList({
  listing,
  canEdit,
}: {
  listing: CategoryListRead
  canEdit: boolean
}) {
  const router = useRouter()
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function run(action: () => Promise<{ ok: boolean; message?: string }>) {
    setBusy(true)
    setError(null)
    const result = await action()
    setBusy(false)
    if (result.ok) {
      setName('')
      router.refresh()
      return
    }
    setError(result.message ?? 'No se pudo guardar')
  }

  return (
    <div className="space-y-4">
      {error && <Notice tone="danger" title={error} />}

      <table className="w-full text-sm">
        <thead className="border-b text-left text-muted-foreground">
          <tr>
            <th className="py-2">Rubro</th>
            <th className="py-2">Productos</th>
            <th className="py-2">Cómo llega escrito</th>
            {canEdit && <th className="py-2" />}
          </tr>
        </thead>
        <tbody>
          {listing.items.map(category => (
            <tr key={category.id} className="border-b align-top">
              <td className="py-2 font-medium">{category.name}</td>
              <td className="amount py-2">{count(category.product_count)}</td>
              <td className="py-2">
                {/* Cada forma escrita, en su píldora: son datos, no una frase. */}
                {category.aliases.length === 0 ? (
                  <span className="text-muted-foreground">—</span>
                ) : (
                  <span className="flex flex-wrap gap-1.5">
                    {category.aliases.map(alias => (
                      <Badge
                        key={alias.id}
                        tone={pill('neutral', isUnconfirmedCategoryAlias(alias.source))}
                      >
                        <Code value={alias.text_original} />
                      </Badge>
                    ))}
                  </span>
                )}
              </td>
              {canEdit && (
                <td className="py-2 text-right">
                  <div className="flex justify-end gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      disabled={busy}
                      onClick={() => {
                        const next = window.prompt('Nombre del rubro', category.name)
                        if (next && next !== category.name) {
                          void run(() => renameCategory(category.id, next))
                        }
                      }}
                    >
                      Renombrar
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      disabled={busy}
                      onClick={() => void run(() => deleteCategory(category.id))}
                    >
                      Eliminar
                    </Button>
                  </div>
                </td>
              )}
            </tr>
          ))}
          <tr className="border-b align-top">
            <td className="py-2 font-medium text-muted-foreground">Sin rubro</td>
            <td className="amount py-2">{count(listing.unclassified_count)}</td>
            <td className="py-2 text-muted-foreground">
              El producto llegó sin categoría, o con una que todavía no está asignada
            </td>
            {canEdit && <td />}
          </tr>
        </tbody>
      </table>

      <p className="text-sm text-muted-foreground">
        {count(listing.total_products)} productos en total. La suma de los rubros más «sin rubro» da
        ese número: nada queda afuera del corte.
      </p>

      {canEdit && (
        <form
          className="flex flex-wrap items-end gap-2"
          onSubmit={event => {
            event.preventDefault()
            if (name.trim()) void run(() => createCategory(name.trim()))
          }}
        >
          <label className="text-sm">
            <span className="mb-1 block text-muted-foreground">Agregar un rubro</span>
            <Input value={name} onChange={event => setName(event.target.value)} maxLength={100} />
          </label>
          {/* Agregar un rubro es la tarea de esta pantalla: su único naranja. */}
          <Button type="submit" variant="brand" disabled={busy || !name.trim()}>
            Agregar
          </Button>
        </form>
      )}
    </div>
  )
}
