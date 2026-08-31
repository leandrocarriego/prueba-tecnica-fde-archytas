'use client'

import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { Sale } from '@/lib/sales/types'

/**
 * Corregir una venta apartada, o cargar el valor que una persona estima (RF-38, RF-39).
 *
 * Los cuatro campos, y no sólo el producto: la fecha que faltaba, el total que
 * no vino, la cantidad imposible y el producto que no existe son cuatro motivos
 * distintos por los que una venta queda afuera, y cada uno se arregla cargando
 * lo suyo.
 *
 * **La casilla de estimado no es un detalle de formulario.** Es lo que separa
 * saber de suponer: todo indicador que sume esta venta va a declarar que uno de
 * sus valores lo estimó una persona (RF-40), y sin esta casilla ese aviso no
 * puede encenderse nunca.
 */
export function SaleCorrection({
  sale,
  disabled,
  onSubmit,
}: {
  sale: Sale
  disabled: boolean
  onSubmit: (
    values: {
      sold_on?: string
      product_code?: string
      quantity?: number
      total?: string
    },
    isEstimated: boolean
  ) => void
}) {
  const [open, setOpen] = useState(false)
  const [soldOn, setSoldOn] = useState(sale.sold_on ?? '')
  const [productCode, setProductCode] = useState(sale.product_code ?? '')
  const [quantity, setQuantity] = useState(sale.quantity == null ? '' : String(sale.quantity))
  const [total, setTotal] = useState(sale.total ?? '')
  const [isEstimated, setIsEstimated] = useState(false)

  if (!open) {
    return (
      <Button type="button" variant="outline" disabled={disabled} onClick={() => setOpen(true)}>
        Corregir
      </Button>
    )
  }

  return (
    <div className="space-y-2 text-left">
      <div className="flex flex-wrap gap-2">
        <label className="text-xs text-muted-foreground">
          Fecha
          <Input
            className="mt-1"
            type="date"
            value={soldOn}
            onChange={event => setSoldOn(event.target.value)}
          />
        </label>
        <label className="text-xs text-muted-foreground">
          Producto
          <Input
            className="mt-1"
            value={productCode}
            onChange={event => setProductCode(event.target.value)}
          />
        </label>
        <label className="text-xs text-muted-foreground">
          Cantidad
          <Input
            className="mt-1 max-w-28"
            type="number"
            value={quantity}
            onChange={event => setQuantity(event.target.value)}
          />
        </label>
        <label className="text-xs text-muted-foreground">
          Total
          <Input
            className="mt-1 max-w-36"
            type="number"
            min={0}
            value={total}
            onChange={event => setTotal(event.target.value)}
          />
        </label>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={isEstimated}
          onChange={event => setIsEstimated(event.target.checked)}
        />
        No se puede saber el valor exacto: lo cargo estimado
      </label>

      <div className="flex gap-2">
        <Button
          type="button"
          disabled={disabled}
          onClick={() => {
            // Sólo viaja lo que la persona escribió. Mandar un campo vacío no
            // borra el valor que ya estaba: la corrección es para completar.
            onSubmit(
              {
                ...(soldOn ? { sold_on: soldOn } : {}),
                ...(productCode ? { product_code: productCode } : {}),
                ...(quantity ? { quantity: Number(quantity) } : {}),
                ...(total ? { total } : {}),
              },
              isEstimated
            )
            setOpen(false)
          }}
        >
          Guardar
        </Button>
        <Button type="button" variant="outline" disabled={disabled} onClick={() => setOpen(false)}>
          Cancelar
        </Button>
      </div>
    </div>
  )
}
