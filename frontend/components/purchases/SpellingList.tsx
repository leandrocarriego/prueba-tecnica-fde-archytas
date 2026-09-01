'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { dropAlias } from '@/app/actions/purchases'
import { Code } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatMoment } from '@/lib/catalog/format'
import type { Supplier, SupplierAlias } from '@/lib/purchases/types'
import { isUnconfirmedSupplierAlias, pill } from '@/lib/ui/tone'
import { Notice } from '@/components/ui/notice'

/**
 * Las grafías guardadas, y el botón que deja una sin efecto.
 *
 * Cada una dice **quién** la decidió y cuándo (RF-51). El nombre lo resuelve la
 * ruta con `ActorDirectory`: `purchases` guarda el id y no puede nombrar a nadie
 * sin importar `identity`. Una grafía que el sistema reconoció solo no tiene
 * autor, y lo dice así en vez de inventar uno.
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
      {error && <Notice tone="danger" title={error} />}

      <table className="w-full text-sm">
        <thead className="border-b text-left text-muted-foreground">
          <tr>
            <th className="py-2">Cómo llega escrito</th>
            <th className="py-2">Proveedor</th>
            <th className="py-2">Quién y cuándo</th>
            {canEdit && <th className="py-2" />}
          </tr>
        </thead>
        <tbody>
          {aliases.map(alias => (
            <tr key={alias.id} className="border-b align-top">
              <td className="py-2">
                {/*
                 * `RF-08`: la que reconoció el sistema va punteada; la que
                 * asignó una persona, no. Es la misma píldora que la ficha del
                 * proveedor, porque es el mismo dato.
                 */}
                <Badge tone={pill('neutral', isUnconfirmedSupplierAlias(alias.source))}>
                  <Code value={alias.text_original} />
                </Badge>
              </td>
              <td className="py-2">{names.get(alias.supplier_id) ?? '—'}</td>
              <td className="py-2 text-muted-foreground">
                {alias.source === 'OBSERVED'
                  ? 'Reconocida por el sistema'
                  : `La asignó ${alias.created_by_name ?? 'alguien que ya no tiene cuenta'}`}
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
