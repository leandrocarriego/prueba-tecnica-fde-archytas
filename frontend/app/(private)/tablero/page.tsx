import Link from 'next/link'

import { NoPermission } from '@/components/common/NoPermission'
import { PeriodPicker } from '@/components/sales/PeriodPicker'
import { fetchFromApi } from '@/lib/api/server'
import { count, day, money } from '@/lib/format'
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
    return <NoPermission what="el tablero del negocio" />
  }

  const ranOut = (catalog?.stock ?? []).filter(cut => cut.ran_out)

  return (
    <main className="mx-auto max-w-5xl space-y-10 p-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Tablero</h1>
        <p className="text-sm text-muted-foreground">
          Cada corte elige su propio período, y cambiar uno no mueve los demás.
        </p>
      </header>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Facturado</h2>
        <p className="text-sm text-muted-foreground">
          {sales.since || sales.until
            ? `Del ${day(sales.since)} al ${day(sales.until)}.`
            : 'Todo el histórico.'}
        </p>
        <PeriodPicker
          fromName="desde"
          toName="hasta"
          from={filters.desde}
          to={filters.hasta}
          keep={{ cat_desde: filters.cat_desde, cat_hasta: filters.cat_hasta }}
        />
        <p className="text-4xl font-semibold">{money(sales.invoiced.value)}</p>
        <p className="text-sm text-muted-foreground">
          {count(sales.invoiced.sales)} ventas sumadas ·{' '}
          {sales.invoiced.excluded === 0 ? (
            'no se excluyó ningún registro'
          ) : (
            /*
              RF-26: desde el número excluido se llega a los registros que
              excluyó. Antes el enlace aparecía sólo si había apartadas, y las
              unificadas no estaban en ninguna cola: la mitad de lo excluido no
              se podía ver desde ningún lado.
            */
            <Link className="underline" href="/ventas/revision">
              {count(sales.invoiced.excluded)} registros excluidos
            </Link>
          )}
          {sales.invoiced.merged > 0 &&
            ` · ${count(sales.invoiced.merged)} de ellos los unificó el sistema solo`}
          {sales.invoiced.has_estimates && ' · incluye valores estimados por una persona'}.
        </p>
        {sales.held_total > 0 && (
          <p className="text-sm">
            <Link className="underline" href="/ventas/revision">
              {sales.held_total} ventas apartadas esperan una decisión
            </Link>
            {sales.pending_groups > 0 && ` · ${sales.pending_groups} grupos de repetidas`}.
          </p>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Facturado por mes</h2>
        {sales.by_month.length === 0 ? (
          <p className="text-sm text-muted-foreground">Todavía no hay ventas para mostrar.</p>
        ) : (
          <table className="w-full max-w-xl text-sm">
            <tbody>
              {sales.by_month.map(month => (
                <tr key={month.month} className="border-b">
                  <td className="py-2">{day(month.month)}</td>
                  <td className="py-2 text-right">{money(month.total)}</td>
                  <td className="py-2 text-right text-muted-foreground">
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
              {catalog.since || catalog.until
                ? `Del ${day(catalog.since)} al ${day(catalog.until)}.`
                : 'Todo el histórico. Sin fecha de inicio el corte de stock no tiene con qué comparar.'}
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
            {catalog.price_curve.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Todavía no hay historial de precios en este período.
              </p>
            ) : (
              <table className="w-full max-w-xl text-sm">
                <tbody>
                  {catalog.price_curve.map(point => (
                    <tr key={point.month} className="border-b">
                      <td className="py-2">{day(point.month)}</td>
                      <td className="py-2 text-right">{money(point.average_price)}</td>
                      <td className="py-2 text-right text-muted-foreground">
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
            <p className="text-sm text-muted-foreground">
              {count(catalog.stock.length)} productos con foto al principio y al final del período ·{' '}
              {catalog.stock_excluded === 0
                ? 'ninguno quedó afuera'
                : `${count(catalog.stock_excluded)} quedaron afuera por no tener foto en algún extremo`}
              .{ranOut.length > 0 && ` ${ranOut.length} quedaron sin stock al final.`}
            </p>
            {ranOut.length > 0 && (
              <ul className="text-sm">
                {ranOut.slice(0, 20).map(cut => (
                  <li key={cut.product_id}>
                    {cut.code} — {cut.description}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-medium">Productos nuevos</h2>
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
    </main>
  )
}
