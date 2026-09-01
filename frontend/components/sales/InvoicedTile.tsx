import { Tile } from '@/components/common/Tile'
import { Money } from '@/components/ui/amount'
import { count } from '@/lib/format'
import type { SalesDashboard } from '@/lib/sales/types'

/**
 * Lo facturado en el período, que es el primer número del tablero (`RF-07`).
 *
 * Va con los registros que dejó afuera pegados abajo, y no en una nota al pie:
 * el número y su reparo se leen juntos o no se leen. `RF-16` cierra el mismo
 * lazo por el otro lado —cuando no se excluyó nada, se dice con todas las
 * letras—: un silencio ahí es indistinguible de un indicador que no miró.
 */
export function InvoicedTile({ sales }: { sales: SalesDashboard }) {
  const { invoiced } = sales

  return (
    <Tile
      label="Facturado en el período"
      value={<Money value={invoiced.value} as="span" />}
      sub={
        <>
          {count(invoiced.sales)} ventas sumadas ·{' '}
          {invoiced.excluded === 0
            ? 'no se excluyó ningún registro'
            : `${count(invoiced.excluded)} registros excluidos`}
          {invoiced.has_estimates && ' · incluye valores estimados por una persona'}.
        </>
      }
    />
  )
}
