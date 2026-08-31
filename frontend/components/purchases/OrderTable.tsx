'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { dismissRepeat, resolveOrder } from '@/app/actions/purchases'
import { Button } from '@/components/ui/button'
import { count, day, money } from '@/lib/format'
import type { PurchaseOrder, Supplier } from '@/lib/purchases/types'

/**
 * Las órdenes de compra, con desde cuándo el sistema las viene mirando.
 *
 * Ese matiz importa: el portal publica **una** fecha, la del pedido, y no dice
 * desde cuándo una orden está en su estado. Lo que se muestra es lo que esta
 * plataforma observó, y para las que ya estaban antes de la puesta en marcha se
 * dice cuántos días pasaron desde el pedido (RF-49), que es otra cosa.
 */
export function OrderTable({
  orders,
  suppliers,
  canEdit,
}: {
  orders: PurchaseOrder[]
  /**
   * El padrón, para resolver una orden apartada sin salir de la lista (H8).
   * **No hay pantalla de revisión aparte**: la spec lo decide así y da el
   * motivo — una cola que cuesta tiempo se abandona.
   */
  suppliers: Supplier[]
  canEdit: boolean
}) {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function resolve(orderId: number, supplierId: number) {
    setBusy(true)
    setError(null)
    const result = await resolveOrder(orderId, supplierId)
    setBusy(false)
    if (result.ok) {
      router.refresh()
      return
    }
    setError(result.message)
  }

  async function dismiss(orderId: number) {
    setBusy(true)
    setError(null)
    const result = await dismissRepeat(orderId)
    setBusy(false)
    if (result.ok) {
      router.refresh()
      return
    }
    setError(result.message)
  }

  if (orders.length === 0) {
    return (
      <p className="rounded border border-dashed p-8 text-center text-muted-foreground">
        No hay órdenes que coincidan.
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

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b text-left text-muted-foreground">
            <tr>
              <th className="py-2">Orden</th>
              <th className="py-2">Proveedor</th>
              <th className="py-2">Producto</th>
              <th className="py-2 text-right">Cantidad</th>
              <th className="py-2 text-right">Monto</th>
              <th className="py-2">Estado</th>
              {canEdit && <th className="py-2" />}
            </tr>
          </thead>
          <tbody>
            {orders.map(order => (
              <tr
                key={order.id}
                className={`border-b align-top ${order.is_stalled ? 'bg-warn-surface' : ''}`}
              >
                <td className="py-2">
                  {order.number}
                  <p className="text-xs text-muted-foreground">{day(order.ordered_on)}</p>
                </td>
                <td className="py-2">
                  {order.supplier_name ?? (
                    <span className="text-warn">{order.supplier_text} · sin identificar</span>
                  )}
                  {order.review_reason && (
                    <p className="text-xs text-warn">{order.review_reason}</p>
                  )}
                </td>
                <td className="py-2">{order.product_text}</td>
                <td className="py-2 text-right">{count(order.quantity)}</td>
                <td className="py-2 text-right">{money(order.amount)}</td>
                <td className="py-2">
                  {order.status_text}
                  <p className="text-xs text-muted-foreground">
                    {order.observed_from_start
                      ? `${count(order.days_in_status)} días observada así`
                      : `pedida hace ${count(order.days_since_ordered)} días`}
                    {order.is_stalled && ' · estancada'}
                  </p>
                  {order.repeat_of_number && (
                    <p className="text-xs text-warn">
                      Posible pedido repetido de {order.repeat_of_number}
                    </p>
                  )}
                </td>
                {canEdit && (
                  <td className="space-y-2 py-2 text-right">
                    {order.repeat_of_number && (
                      <Button
                        type="button"
                        variant="outline"
                        disabled={busy}
                        onClick={() => void dismiss(order.id)}
                      >
                        No es repetido
                      </Button>
                    )}
                    {order.review_state === 'PENDING' && (
                      /*
                        H8: la orden apartada se resuelve **acá**, en la misma
                        lista donde se la mira. Elegir el proveedor guarda además
                        esa forma de escribir el nombre como criterio, así que las
                        otras órdenes escritas igual quedan resueltas de una vez
                        y la que llegue después entra ya identificada.

                        No hay forma de dar de alta un proveedor: el padrón son
                        los ocho del portal, y sumar uno es una decisión del
                        negocio que se toma en otro lado (RF-55).
                      */
                      <select
                        className="rounded border px-2 py-1 text-sm"
                        defaultValue=""
                        disabled={busy}
                        onChange={event => {
                          if (event.target.value) {
                            void resolve(order.id, Number(event.target.value))
                          }
                        }}
                      >
                        <option value="">Asignar proveedor…</option>
                        {suppliers.map(supplier => (
                          <option key={supplier.id} value={String(supplier.id)}>
                            {supplier.legal_name}
                          </option>
                        ))}
                      </select>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
