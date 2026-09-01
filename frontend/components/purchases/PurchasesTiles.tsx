import Link from 'next/link'

import { Tile } from '@/components/common/Tile'
import { Money } from '@/components/ui/amount'
import { count } from '@/lib/format'
import type { PurchasesDashboard } from '@/lib/purchases/types'

/**
 * Las tres cuentas de compras de arriba del tablero (guía visual `3b`): lo que
 * se debe, lo que vence esta semana y lo que se pidió y no llegó.
 *
 * **Ninguna de las tres tiene período**, y por eso no hay control de fechas
 * arriba de ellas: «cuánto debo» es una pregunta sobre hoy. La ventana la
 * eligen los cortes que sí son de un período —la facturación, los precios—, que
 * es lo que `RF-05` pide y lo único que pide.
 *
 * La del medio es la única con acento, y sólo cuando hay algo esta semana: un
 * vencimiento es lo que hace falta decidir hoy. Las otras dos informan.
 */
export function PurchasesTiles({ purchases }: { purchases: PurchasesDashboard }) {
  const excluded = purchases.excluded_in_review + purchases.excluded_inconsistent

  return (
    <>
      <Tile
        label="Deuda a proveedores"
        value={<Money value={purchases.owed} as="span" />}
        sub={
          <>
            {count(purchases.open_invoices)}{' '}
            {purchases.open_invoices === 1 ? 'factura abierta' : 'facturas abiertas'}
            {/*
              Lo que el total deja afuera, pegado al total (Artículo II). No es
              una nota al pie: una deuda que oculta que hay tres facturas cuyo
              importe nadie confirmó es una deuda que el cliente va a desmentir.
            */}
            {excluded > 0 && (
              <>
                {' · '}
                <span className="text-warn">
                  {count(excluded)} sin sumar
                  {purchases.excluded_in_review > 0 &&
                    ` (${count(purchases.excluded_in_review)} en revisión)`}
                </span>
              </>
            )}
            .
          </>
        }
      />

      <Tile
        label={`Vence en ${purchases.due_soon_days} días`}
        value={count(purchases.due_soon)}
        accent={purchases.due_soon > 0}
        sub={
          <>
            {purchases.due_soon_without_receipt > 0
              ? `${count(purchases.due_soon_without_receipt)} sin recibo`
              : 'Todas con recibo emitido'}
            {purchases.overdue > 0 && (
              <>
                {' · '}
                <Link className="font-medium text-link hover:underline" href="/calendario">
                  {count(purchases.overdue)} ya vencidas →
                </Link>
              </>
            )}
          </>
        }
      />

      <Tile
        label="OC sin recibir"
        value={count(purchases.orders_pending)}
        sub={
          purchases.orders_stalled > 0 ? (
            <Link className="font-medium text-link hover:underline" href="/ordenes">
              {count(purchases.orders_stalled)} con más de {count(purchases.stalled_days)} días →
            </Link>
          ) : (
            `Ninguna lleva más de ${count(purchases.stalled_days)} días parada.`
          )
        }
      />
    </>
  )
}
