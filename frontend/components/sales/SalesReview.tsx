'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { correctSale, resolveSaleGroup, undoSaleResolution } from '@/app/actions/sales'
import { Button } from '@/components/ui/button'
import { count, day, money } from '@/lib/format'
import type { ReviewQueue } from '@/lib/sales/types'

const FIELDS: Record<string, string> = {
  sold_on: 'la fecha',
  product_code: 'el producto',
  quantity: 'la cantidad',
  total: 'el total',
}

/**
 * Las ventas apartadas: las repetidas enfrentadas, y las rotas con su motivo.
 *
 * Las versiones de una repetida se muestran una al lado de la otra con **los
 * campos en que difieren señalados** (RF-30), que es lo que convierte "estas dos
 * no son iguales" en una decisión que se toma en un segundo.
 */
export function SalesReview({ queue, canEdit }: { queue: ReviewQueue; canEdit: boolean }) {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

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
    <div className="space-y-8">
      {error && (
        <p className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-900">{error}</p>
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Ventas repetidas ({queue.pending_groups})</h2>
        {queue.groups.length === 0 ? (
          <p className="text-sm text-muted-foreground">Ninguna repetida esperando una decisión.</p>
        ) : (
          queue.groups.map(group => (
            <article key={group.code_key} className="space-y-3 rounded border p-4">
              <header>
                <h3 className="font-medium">Código {group.versions[0]?.code}</h3>
                <p className="text-sm text-amber-800">
                  Difieren en{' '}
                  {(group.differences ?? []).map(field => FIELDS[field] ?? field).join(', ')}.
                  Ninguna suma mientras tanto.
                </p>
              </header>

              <table className="w-full text-sm">
                <thead className="border-b text-left text-muted-foreground">
                  <tr>
                    <th className="py-1">Fecha</th>
                    <th className="py-1">Producto</th>
                    <th className="py-1 text-right">Cantidad</th>
                    <th className="py-1 text-right">Total</th>
                    {canEdit && <th className="py-1" />}
                  </tr>
                </thead>
                <tbody>
                  {group.versions.map(version => (
                    <tr key={version.id} className="border-b">
                      <td className="py-1">{day(version.sold_on)}</td>
                      <td className="py-1">{version.product_code ?? '—'}</td>
                      <td className="py-1 text-right">{count(version.quantity)}</td>
                      <td className="py-1 text-right">{money(version.total)}</td>
                      {canEdit && (
                        <td className="py-1 text-right">
                          <Button
                            type="button"
                            variant="outline"
                            disabled={busy}
                            onClick={() =>
                              void run(() => resolveSaleGroup(group.code_key, 'keep', version.id))
                            }
                          >
                            Ésta es la válida
                          </Button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>

              {canEdit && (
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    disabled={busy}
                    onClick={() =>
                      void run(() => resolveSaleGroup(group.code_key, 'distinct', null))
                    }
                  >
                    Son ventas distintas
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={busy}
                    onClick={() => void run(() => undoSaleResolution(group.code_key))}
                  >
                    Deshacer una decisión anterior
                  </Button>
                </div>
              )}
            </article>
          ))
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Ventas con datos rotos ({queue.broken.length})</h2>
        {queue.broken.length === 0 ? (
          <p className="text-sm text-muted-foreground">Ninguna con datos rotos.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b text-left text-muted-foreground">
              <tr>
                <th className="py-2">Código</th>
                <th className="py-2">Fecha</th>
                <th className="py-2">Producto</th>
                <th className="py-2 text-right">Total</th>
                <th className="py-2">Por qué está apartada</th>
                {canEdit && <th className="py-2" />}
              </tr>
            </thead>
            <tbody>
              {queue.broken.map(sale => (
                <tr key={sale.id} className="border-b align-top">
                  <td className="py-2">{sale.code}</td>
                  <td className="py-2">{day(sale.sold_on)}</td>
                  <td className="py-2">{sale.product_code ?? '—'}</td>
                  <td className="py-2 text-right">{money(sale.total)}</td>
                  <td className="py-2 text-amber-800">{sale.reason}</td>
                  {canEdit && (
                    <td className="py-2 text-right">
                      <Button
                        type="button"
                        variant="outline"
                        disabled={busy}
                        onClick={() => {
                          const code = window.prompt(
                            'Código de producto correcto',
                            sale.product_code ?? ''
                          )
                          if (code) {
                            void run(() => correctSale(sale.id, { product_code: code }, false))
                          }
                        }}
                      >
                        Corregir
                      </Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
