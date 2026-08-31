'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { repointAlias } from '@/app/actions/categories'
import { revokeRule } from '@/app/actions/triage'
import { Button } from '@/components/ui/button'
import { formatMoment } from '@/lib/catalog/format'
import type { Category, CategoryAlias, Rule } from '@/lib/catalog/types'

/**
 * Las equivalencias guardadas: qué forma escrita significa qué rubro (RF-27).
 *
 * Las dos acciones no son la misma y la diferencia es toda la H5:
 *
 * * **Corregir** reapunta la equivalencia y **reasigna** los productos que
 *   dependían de ella. Nadie vuelve a la cola de revisión (RF-28, RF-29).
 * * **Dejar sin efecto** la borra y esos productos **vuelven** a revisión
 *   (RF-30, RF-31).
 *
 * Las dieciocho formas que vinieron con el sistema son reglas como cualquier
 * otra, así que las dos acciones también alcanzan a ellas.
 */
export function AliasList({
  aliases,
  categories,
  rules,
  canEdit,
}: {
  aliases: CategoryAlias[]
  categories: Category[]
  rules: Rule[]
  canEdit: boolean
}) {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const byRule = new Map(rules.map(rule => [rule.id, rule]))
  const byCategory = new Map(categories.map(category => [category.id, category.name]))

  async function run(action: () => Promise<{ ok: boolean; message?: string }>) {
    setBusy(true)
    setError(null)
    const result = await action()
    setBusy(false)
    if (result.ok) {
      router.refresh()
      return
    }
    setError(result.message ?? 'No se pudo guardar')
  }

  return (
    <div className="space-y-4">
      {error && (
        <p className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-900">{error}</p>
      )}

      <table className="w-full text-sm">
        <thead className="border-b text-left text-muted-foreground">
          <tr>
            <th className="py-2">Forma escrita</th>
            <th className="py-2">Rubro</th>
            <th className="py-2">Quién la decidió</th>
            {canEdit && <th className="py-2" />}
          </tr>
        </thead>
        <tbody>
          {aliases.map(alias => {
            const rule = alias.rule_id === null ? undefined : byRule.get(alias.rule_id)
            return (
              <tr key={alias.id} className="border-b align-top">
                <td className="py-2 font-mono">{alias.text_original}</td>
                <td className="py-2">{byCategory.get(alias.category_id) ?? '—'}</td>
                <td className="py-2 text-muted-foreground">
                  {rule?.created_by_name ?? 'Sembrado en la puesta en marcha'}
                  {rule?.created_at && ` · ${formatMoment(rule.created_at)}`}
                  {rule?.updated_at && ` · corregida ${formatMoment(rule.updated_at)}`}
                </td>
                {canEdit && (
                  <td className="py-2 text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        disabled={busy || alias.rule_id === null}
                        onClick={() => {
                          const name = window.prompt(
                            'Rubro nuevo para esta forma escrita:\n' +
                              categories.map(item => `${item.id} — ${item.name}`).join('\n')
                          )
                          const chosen = Number(name)
                          if (alias.rule_id !== null && chosen) {
                            void run(() => repointAlias(alias.rule_id as number, chosen))
                          }
                        }}
                      >
                        Corregir
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        disabled={busy || alias.rule_id === null}
                        onClick={() => {
                          if (alias.rule_id !== null) {
                            void run(() => revokeRule(alias.rule_id as number))
                          }
                        }}
                      >
                        Dejar sin efecto
                      </Button>
                    </div>
                  </td>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>

      <p className="text-sm text-muted-foreground">
        Corregir una equivalencia reasigna sus productos al rubro nuevo. Dejarla sin efecto los
        devuelve a revisión: no es lo mismo, y por eso son dos botones.
      </p>
    </div>
  )
}
