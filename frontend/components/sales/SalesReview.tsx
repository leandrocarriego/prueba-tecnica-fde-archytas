'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { correctSale, resolveSaleGroup, undoSaleResolution } from '@/app/actions/sales'
import { SaleCorrection } from '@/components/sales/SaleCorrection'
import { Code, Day, Money } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Notice } from '@/components/ui/notice'
import { Empty } from '@/components/ui/state'
import { formatMoment } from '@/lib/catalog/format'
import { count } from '@/lib/format'
import type { ResolvedGroup, ReviewQueue, Sale } from '@/lib/sales/types'
import { isUnconfirmedSale, pill, saleTone } from '@/lib/ui/tone'

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
export function SalesReview({
  queue,
  resolved,
  discarded,
  canEdit,
}: {
  queue: ReviewQueue
  resolved: ResolvedGroup[]
  discarded: Sale[]
  canEdit: boolean
}) {
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
      {error && <Notice tone="danger" title={error} />}

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Ventas repetidas ({queue.pending_groups})</h2>
        {queue.groups.length === 0 ? (
          <Empty title="Ninguna repetida esperando una decisión." />
        ) : (
          queue.groups.map(group => (
            <Card key={group.code_key} className="space-y-3 p-5">
              <header>
                <h3 className="font-medium">Código {group.versions[0]?.code}</h3>
                <p className="text-sm text-warn">
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
                      <Day value={version.sold_on} cell className="py-1 text-left" />
                      <Code value={version.product_code} cell className="py-1 text-left" />
                      <td className="amount py-1 text-right">{count(version.quantity)}</td>
                      <td className="py-1 text-right">
                        <Money value={version.total} />
                        {/*
                         * `RF-08`: una venta estimada o apartada no está
                         * confirmada, y se ve punteada sin leer la etiqueta.
                         */}
                        <Badge
                          className="ml-2"
                          tone={pill(saleTone(version.state), isUnconfirmedSale(version))}
                        >
                          {version.is_estimated ? 'Estimada' : 'Apartada'}
                        </Badge>
                      </td>
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

              {/*
                Acá no va el deshacer, y antes iba. Un grupo que está en esta
                lista está **pendiente**: por definición no tiene decisión que
                revertir, así que el botón sólo podía contestar «esa venta no
                tiene una resolución que deshacer». Y apenas alguien decidía, el
                grupo se iba de la cola y el botón se iba con él: RF-35 no tenía
                ningún camino. Ahora vive en «Casos resueltos», que es donde hay
                algo que deshacer.
              */}
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
                </div>
              )}
            </Card>
          ))
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Ventas con datos rotos ({queue.broken.length})</h2>
        {queue.broken.length === 0 ? (
          <Empty title="Ninguna con datos rotos." />
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
                  <Code value={sale.code} cell className="py-2 text-left" />
                  <Day value={sale.sold_on} cell className="py-2 text-left" />
                  <Code value={sale.product_code} cell className="py-2 text-left" />
                  <Money value={sale.total} cell className="py-2" />
                  <td className="py-2 text-warn">{sale.reason}</td>
                  {canEdit && (
                    <td className="py-2 text-right">
                      <SaleCorrection
                        sale={sale}
                        disabled={busy}
                        onSubmit={(values, isEstimated) =>
                          void run(() => correctSale(sale.id, values, isEstimated))
                        }
                      />
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/*
        RF-34, RF-35 y RF-36, que hasta acá no tenían dónde ocurrir.
        Un caso decidido se va de la cola —eso es RF-37 y está bien— y se iba
        también de la pantalla, llevándose con él la versión descartada al lado
        de la elegida, el quién y el cuándo, y el deshacer.

        No se solapa con «Ventas que no suman»: esa lista contesta *qué dejó
        afuera cada indicador* (RF-26) y mezcla lo que el sistema unificó solo
        con lo que decidió una persona. Ésta contesta *qué decidió alguien*, y
        es la única de las dos sobre la que se puede volver atrás.
      */}
      <section className="space-y-3">
        <h2 className="text-lg font-medium">Casos resueltos ({resolved.length})</h2>
        {resolved.length === 0 ? (
          <Empty title="Todavía nadie decidió sobre una repetida." />
        ) : (
          resolved.map(group => (
            <Card key={group.code_key} className="space-y-3 p-5">
              <header className="space-y-1">
                <h3 className="font-medium">Código {group.versions[0]?.code}</h3>
                <p className="text-sm text-muted-foreground">
                  {group.action === 'distinct'
                    ? 'Se declararon ventas distintas: las dos suman.'
                    : 'Se eligió una versión: sólo ésa suma.'}{' '}
                  {/* RF-36: quién y cuándo. Sin nombre se dice que no se sabe,
                      en vez de escribir un id que a nadie le dice nada. */}
                  Lo decidió {group.resolved_by_name ?? 'alguien que ya no tiene acceso'} el{' '}
                  {formatMoment(group.resolved_at)}.
                </p>
              </header>

              <table className="w-full text-sm">
                <thead className="border-b text-left text-muted-foreground">
                  <tr>
                    <th className="py-1">Fecha</th>
                    <th className="py-1">Producto</th>
                    <th className="py-1 text-right">Cantidad</th>
                    <th className="py-1 text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {group.versions.map(version => (
                    <tr key={version.id} className="border-b">
                      <Day value={version.sold_on} cell className="py-1 text-left" />
                      <Code value={version.product_code} cell className="py-1 text-left" />
                      <td className="amount py-1 text-right">{count(version.quantity)}</td>
                      <td className="py-1 text-right">
                        <Money value={version.total} />
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

              {canEdit && (
                <Button
                  type="button"
                  variant="outline"
                  disabled={busy}
                  onClick={() => void run(() => undoSaleResolution(group.code_key))}
                >
                  Deshacer esta decisión
                </Button>
              )}
            </Card>
          ))
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Ventas que no suman ({discarded.length})</h2>
        <p className="text-sm text-muted-foreground">
          No esperan una decisión: o el sistema las unificó solo por ser idénticas a otra, o alguien
          eligió otra versión. Están acá porque forman parte de lo que cada indicador excluyó, y un
          número que dice cuánto dejó afuera tiene que dejar ver qué dejó afuera.
        </p>
        {discarded.length === 0 ? (
          <Empty title="Ninguna." />
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b text-left text-muted-foreground">
              <tr>
                <th className="py-2">Código</th>
                <th className="py-2">Fecha</th>
                <th className="py-2">Producto</th>
                <th className="py-2 text-right">Total</th>
                <th className="py-2">Por qué no suma</th>
              </tr>
            </thead>
            <tbody>
              {discarded.map(sale => (
                <tr key={sale.id} className="border-b align-top">
                  <Code value={sale.code} cell className="py-2 text-left" />
                  <Day value={sale.sold_on} cell className="py-2 text-left" />
                  <Code value={sale.product_code} cell className="py-2 text-left" />
                  <Money value={sale.total} cell className="py-2" />
                  <td className="py-2 text-muted-foreground">{sale.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
