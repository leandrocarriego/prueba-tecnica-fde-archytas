'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { undoSaleResolution } from '@/app/actions/sales'
import { Code, Day, Money } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Notice } from '@/components/ui/notice'
import { Empty } from '@/components/ui/state'
import { formatMoment } from '@/lib/catalog/format'
import { count } from '@/lib/format'
import type { ResolvedGroup } from '@/lib/sales/types'
import { isUnconfirmedSale, pill, saleTone } from '@/lib/ui/tone'

/**
 * Las ventas repetidas sobre las que alguien ya decidió, y la vuelta atrás.
 *
 * `RF-34`, `RF-35` y `RF-36` de la 009, que son tres cosas y una sola pantalla:
 * la versión descartada se sigue viendo al lado de la elegida, el caso dice qué
 * se decidió, quién y cuándo, y desde ahí la decisión se puede deshacer.
 *
 * **Vive dentro de «Decisiones guardadas»**, y no en una sección propia al lado:
 * una venta resuelta y una regla aprendida son la misma clase de cosa —algo que
 * alguien ya decidió y que se puede revocar— y tenerlas en dos bloques separados
 * obligaba a saber de antemano en cuál buscar. Por eso este componente dibuja la
 * lista y no su marco: el título, la explicación y las pestañas los pone
 * `SavedDecisions`, que es quien sabe qué más hay al lado.
 *
 * Y vive en la cola y no en el listado de ventas porque deshacer devuelve la
 * venta acá —el caso se reabre solo con el evento que publica `sales`—, así que
 * la consecuencia aparece en la misma pantalla donde se pidió.
 */
export function ResolvedSales({ groups }: { groups: ResolvedGroup[] }) {
  const router = useRouter()
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function undo(codeKey: string) {
    setBusy(codeKey)
    setError(null)
    const result = await undoSaleResolution(codeKey)
    setBusy(null)
    if (result.ok) {
      router.refresh()
      return
    }
    setError(result.message ?? 'No se pudo deshacer')
  }

  return (
    <div className="space-y-3">
      {error && <Notice tone="danger" title={error} />}

      {groups.length === 0 ? (
        <Empty title="Todavía nadie decidió sobre una repetida." />
      ) : (
        <div className="space-y-3">
          {groups.map(group => (
            <Card key={group.code_key} className="space-y-3 p-5">
              <header className="space-y-1">
                <h3 className="font-medium">Código {group.versions[0]?.code}</h3>
                <p className="text-sm text-muted-foreground">
                  {group.action === 'distinct'
                    ? 'Se declararon ventas distintas: las dos suman.'
                    : 'Se eligió una versión: sólo ésa suma.'}{' '}
                  {/*
                    RF-36: quién y cuándo. Sin nombre se dice que no se sabe, en
                    vez de escribir un id que a nadie le dice nada.
                  */}
                  Lo decidió {group.resolved_by_name ?? 'alguien que ya no tiene acceso'} el{' '}
                  {formatMoment(group.resolved_at)}.
                </p>
              </header>

              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted">
                      <th className="section-label px-3 py-2 text-left">Fecha</th>
                      <th className="section-label px-3 py-2 text-left">Producto</th>
                      <th className="section-label px-3 py-2 text-right">Cantidad</th>
                      <th className="section-label px-3 py-2 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.versions.map(version => (
                      <tr key={version.id} className="border-b border-border last:border-0">
                        <Day value={version.sold_on} cell className="px-3 py-2 text-left" />
                        <Code value={version.product_code} cell className="px-3 py-2 text-left" />
                        <td className="amount px-3 py-2 text-right">{count(version.quantity)}</td>
                        <td className="px-3 py-2 text-right">
                          <Money value={version.total} as="span" />
                          {/* RF-34: la descartada se sigue viendo, y se ve que lo es. */}
                          <Badge
                            className="ml-2"
                            tone={pill(saleTone(version.state), isUnconfirmedSale(version))}
                          >
                            {version.state === 'DISCARDED' ? 'Descartada' : 'Cuenta'}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <Button
                type="button"
                variant="outline"
                disabled={busy === group.code_key}
                onClick={() => void undo(group.code_key)}
              >
                Deshacer esta decisión
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
