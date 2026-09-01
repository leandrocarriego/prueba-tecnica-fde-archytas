import Link from 'next/link'

import { NoPermission } from '@/components/common/NoPermission'
import { PeriodPicker } from '@/components/sales/PeriodPicker'
import { Code, Day, Money } from '@/components/ui/amount'
import { Button } from '@/components/ui/button'
import { Notice } from '@/components/ui/notice'
import { Empty } from '@/components/ui/state'
import { fetchFromApi } from '@/lib/api/server'
import { count } from '@/lib/format'
import type { CatalogDashboard, SalesDashboard } from '@/lib/sales/types'

export const metadata = {
  title: 'Tablero — Plataforma Cordillera',
}

interface PageProps {
  searchParams: Promise<{
    desde?: string
    hasta?: string
    cat_desde?: string
    cat_hasta?: string
  }>
}

/** Una ventana como la espera el backend, u omitida si no se eligió. */
function period(since?: string, until?: string): string {
  const query = new URLSearchParams()
  if (since) query.set('since', since)
  if (until) query.set('until', until)
  return query.toString()
}

/**
 * Lo que un indicador dejó afuera, **arriba** del número (`RF-14`, `RF-15`).
 *
 * Es la única parte de esta feature donde cambia el orden del contenido, y la
 * spec lo pide con todas las letras: el aviso estaba debajo del importe, en un
 * renglón gris del mismo tamaño que el resto, así que se leía el número —o se
 * lo copiaba a un mensaje— sin haber pasado nunca por la advertencia de que no
 * estaba completo. Primero se dice si se puede confiar en el dato; después se
 * lo muestra.
 *
 * Y lleva su salida (`RF-15`): un aviso que dice «faltan 12 registros» y no
 * dice dónde verlos no es un aviso, es una queja.
 */
function Excluded({
  howMany,
  href,
  children,
}: {
  howMany: number
  href?: string
  children?: React.ReactNode
}) {
  if (howMany === 0) return null

  return (
    <Notice
      tone="warn"
      title={
        howMany === 1
          ? 'Este total deja 1 registro afuera'
          : `Este total deja ${count(howMany)} registros afuera`
      }
      action={
        href ? (
          <Button asChild variant="outline" size="sm">
            <Link href={href}>Ver cuáles</Link>
          </Button>
        ) : undefined
      }
    >
      {children}
    </Notice>
  )
}

/**
 * Cómo viene el negocio, con lo que cada número dejó afuera (009).
 *
 * **Lo excluido va pegado al número, no al pie.** RF-25 pide que cada indicador
 * informe cuántos registros dejó afuera, y RF-27 que lo diga incluso cuando no
 * dejó ninguno: "cero excluidos" es una respuesta, y un silencio no.
 */
export default async function DashboardPage({ searchParams }: PageProps) {
  const filters = await searchParams

  // **Dos ventanas, no una.** El backend son dos endpoints justamente para que
  // cada corte elija su período por separado (RF-05), y hasta acá la pantalla
  // les mandaba la misma a los dos y no ofrecía ningún control: el período se
  // cambiaba editando la URL a mano, y la leyenda de abajo era falsa.
  const [sales, catalog] = await Promise.all([
    fetchFromApi<SalesDashboard>(`/dashboard/sales?${period(filters.desde, filters.hasta)}`),
    fetchFromApi<CatalogDashboard>(
      `/dashboard/catalog?${period(filters.cat_desde, filters.cat_hasta)}`
    ),
  ])

  if (sales === null) {
    return <NoPermission what="el tablero del negocio" isHome />
  }

  const ranOut = (catalog?.stock ?? []).filter(cut => cut.ran_out)

  return (
    <div className="space-y-10">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Tablero</h1>
        <p className="text-sm text-muted-foreground">
          Cada corte elige su propio período, y cambiar uno no mueve los demás.
        </p>
      </header>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Facturado</h2>
        <p className="text-sm text-muted-foreground">
          {sales.since || sales.until ? (
            <>
              Del <Day value={sales.since} /> al <Day value={sales.until} />.
            </>
          ) : (
            'Todo el histórico.'
          )}
        </p>
        <PeriodPicker
          fromName="desde"
          toName="hasta"
          from={filters.desde}
          to={filters.hasta}
          keep={{ cat_desde: filters.cat_desde, cat_hasta: filters.cat_hasta }}
        />
        {/*
          RF-26: desde lo excluido se llega a los registros que excluyó, y por
          eso el aviso lleva el botón que lleva ahí.
        */}
        <Excluded howMany={sales.invoiced.excluded} href="/ventas/revision">
          Ninguno de esos registros suma en este total.
          {sales.invoiced.merged > 0 &&
            ` ${count(sales.invoiced.merged)} de ellos los unificó el sistema solo.`}
        </Excluded>

        <Money value={sales.invoiced.value} as="div" className="text-4xl font-semibold" />

        <p className="text-sm text-muted-foreground">
          {count(sales.invoiced.sales)} ventas sumadas ·{' '}
          {/* `RF-16`: cero excluidos se dice con todas las letras. */}
          {sales.invoiced.excluded === 0
            ? 'no se excluyó ningún registro'
            : `${count(sales.invoiced.excluded)} registros excluidos`}
          {sales.invoiced.has_estimates && ' · incluye valores estimados por una persona'}.
        </p>
        {sales.held_total > 0 && (
          <p className="text-sm">
            <Link className="text-link hover:underline" href="/ventas/revision">
              {sales.held_total} ventas apartadas esperan una decisión
            </Link>
            {sales.pending_groups > 0 && ` · ${sales.pending_groups} grupos de repetidas`}.
          </p>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Facturado por mes</h2>
        {sales.by_month.length === 0 ? (
          <Empty title="Todavía no hay ventas para mostrar." />
        ) : (
          <table className="w-full max-w-xl text-sm">
            <tbody>
              {sales.by_month.map(month => (
                <tr key={month.month} className="border-b">
                  <Day value={month.month} cell className="py-2 text-left" />
                  <Money value={month.total} cell className="py-2" />
                  <td className="amount py-2 text-right text-muted-foreground">
                    {count(month.sales)} ventas
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {catalog && (
        <>
          <section className="space-y-3">
            <h2 className="text-lg font-medium">Catálogo</h2>
            <p className="text-sm text-muted-foreground">
              {catalog.since || catalog.until ? (
                <>
                  Del <Day value={catalog.since} /> al <Day value={catalog.until} />.
                </>
              ) : (
                'Todo el histórico. Sin fecha de inicio el corte de stock no tiene con qué comparar.'
              )}
            </p>
            <PeriodPicker
              fromName="cat_desde"
              toName="cat_hasta"
              from={filters.cat_desde}
              to={filters.cat_hasta}
              keep={{ desde: filters.desde, hasta: filters.hasta }}
            />
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-medium">Precios del proveedor</h2>
            <Excluded howMany={catalog.price_curve_excluded}>
              No entran en la curva: les falta el precio o la fecha con que compararlos.
            </Excluded>

            {catalog.price_curve.length === 0 ? (
              <Empty title="Todavía no hay historial de precios en este período." />
            ) : (
              <table className="w-full max-w-xl text-sm">
                <tbody>
                  {catalog.price_curve.map(point => (
                    <tr key={point.month} className="border-b">
                      <Day value={point.month} cell className="py-2 text-left" />
                      <Money value={point.average_price} cell className="py-2" />
                      <td className="amount py-2 text-right text-muted-foreground">
                        {count(point.changes)} cambios
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <p className="text-sm text-muted-foreground">
              {catalog.price_curve_excluded === 0
                ? 'No se excluyó ningún registro de este corte.'
                : `${count(catalog.price_curve_excluded)} registros excluidos.`}
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-medium">Stock</h2>

            {/*
              Lo que excluye el corte es **no tener ninguna foto** que comparar
              —ni una desde el inicio del período, ni una hasta el final—, no que
              falte en uno de los dos extremos: con una sola observación la misma
              foto es la de apertura y la de cierre, y el producto entra al corte
              leyéndose como «no se movió» (`catalog/service.py`, y
              `data-model.md` → *Cómo se arma el corte*). El texto decía lo
              contrario y le atribuía al sistema una exclusión que no hace.
            */}
            <Excluded howMany={catalog.stock_excluded}>
              Quedaron afuera porque no hay ninguna foto de su stock con que comparar en este
              período. No se cuentan como cero: decir cero sería inventar un stock.
            </Excluded>

            <p className="text-sm text-muted-foreground">
              {count(catalog.stock.length)} productos con stock comparable en el período ·{' '}
              {catalog.stock_excluded === 0
                ? 'ninguno quedó afuera'
                : `${count(catalog.stock_excluded)} quedaron afuera por no tener ninguna foto`}
              .
              {ranOut.length > 0 &&
                (ranOut.length === 1
                  ? ' 1 quedó sin stock al final.'
                  : ` ${count(ranOut.length)} quedaron sin stock al final.`)}
            </p>
            {ranOut.length > 0 && (
              <ul className="text-sm">
                {ranOut.slice(0, 20).map(cut => (
                  <li key={cut.product_id}>
                    <Code value={cut.code} /> — {cut.description}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-medium">Productos nuevos</h2>

            <Excluded howMany={catalog.new_products_excluded}>
              No se pudieron fechar dentro del período, así que no se cuentan como nuevos.
            </Excluded>

            <p className="text-sm text-muted-foreground">
              {count(catalog.new_products.length)} productos aparecieron por primera vez en este
              período ·{' '}
              {catalog.new_products_excluded === 0
                ? 'no se excluyó ningún registro'
                : `${count(catalog.new_products_excluded)} registros excluidos`}
              .
            </p>
          </section>
        </>
      )}
    </div>
  )
}
