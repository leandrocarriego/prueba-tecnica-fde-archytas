'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { dropAlias } from '@/app/actions/purchases'
import { Button } from '@/components/ui/button'
import { formatMoment } from '@/lib/catalog/format'
import type { Supplier, SupplierAlias } from '@/lib/purchases/types'

/**
 * Las grafías guardadas, y el botón que deja una sin efecto.
 *
 * Dejarla sin efecto devuelve a revisión **exactamente lo que esa grafía había
 * resuelto** (RF-53). Una factura que alguien decidió una por una no dependía
 * de ella y no vuelve: por eso el botón dice lo que hace y no "borrar".
 */
export function SpellingList({
  aliases,
  suppliers,
  canEdit,
}: {
  aliases: SupplierAlias[]
  suppliers: Supplier[]
  canEdit: boolean
}) {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const names = new Map(suppliers.map(supplier => [supplier.id, supplier.legal_name]))

  async function drop(aliasId: number) {
    setBusy(true)
    setError(null)
    const result = await dropAlias(aliasId)
    setBusy(false)
    if (result.ok) {
      router.refresh()
      return
    }
    setError(result.message)
  }

  return (
    <div className="space-y-4">
      {error && (
        <p className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-900">{error}</p>
      )}

      <table className="w-full text-sm">
        <thead className="border-b text-left text-muted-foreground">
          <tr>
            <th className="py-2">Cómo llega escrito</th>
            <th className="py-2">Proveedor</th>
            <th className="py-2">De dónde salió</th>
            {canEdit && <th className="py-2" />}
          </tr>
        </thead>
        <tbody>
          {aliases.map(alias => (
            <tr key={alias.id} className="border-b align-top">
              <td className="py-2 font-mono">{alias.text_original}</td>
              <td className="py-2">{names.get(alias.supplier_id) ?? '—'}</td>
              <td className="py-2 text-muted-foreground">
                {alias.source === 'OBSERVED' ? 'Reconocida por el sistema' : 'Asignada por alguien'}
                {' · '}
                {formatMoment(alias.created_at)}
              </td>
              {canEdit && (
                <td className="py-2 text-right">
                  <Button
                    type="button"
                    variant="outline"
                    disabled={busy}
                    onClick={() => void drop(alias.id)}
                  >
                    Dejar sin efecto
                  </Button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
