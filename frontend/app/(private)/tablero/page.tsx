import { CategorySpendCard } from '@/components/catalog/CategorySpendCard'
import { NewProductsCard } from '@/components/catalog/NewProductsCard'
import { PriceCurveCard } from '@/components/catalog/PriceCurveCard'
import { RanOutTable } from '@/components/catalog/RanOutTable'
import { StockCard } from '@/components/catalog/StockCard'
import { Excluded } from '@/components/common/Excluded'
import { NoPermission } from '@/components/common/NoPermission'
import { PurchasesTiles } from '@/components/purchases/PurchasesTiles'
import { UpcomingDues } from '@/components/purchases/UpcomingDues'
import { CutHeader } from '@/components/sales/CutHeader'
import { InvoicedTile } from '@/components/sales/InvoicedTile'
import { MonthlyBilling } from '@/components/sales/MonthlyBilling'
import { PeriodPicker } from '@/components/sales/PeriodPicker'
import { SalesQuality } from '@/components/sales/SalesQuality'
import { fetchFromApi } from '@/lib/api/server'
import type { CategoryList } from '@/lib/catalog/types'
import { count } from '@/lib/format'
import type { PurchasesDashboard } from '@/lib/purchases/types'
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
 * Cómo viene el negocio, con la forma que firmó la guía visual (`3b`).
 *
 * El orden de la pantalla **es** el argumento del producto: encabezado, la
 * franja de lo que quedó afuera, recién después los números, y los cortes del
 * catálogo abajo. Primero se dice si se puede confiar en los datos, después se
 * muestran (`RF-07`, `RF-14`); y lo excluido va pegado a cada número, no al pie,
 * porque `RF-25` pide que cada indicador informe cuántos registros dejó afuera
 * y `RF-27` que lo diga incluso cuando no dejó ninguno: «cero excluidos» es una
 * respuesta, y un silencio no.
 *
 * **Cuatro consultas, y cada una puede faltar sin llevarse la pantalla.** Son
 * cuatro secciones distintas del sistema de accesos, así que quién entra decide
 * cuánto tablero hay: el dueño ve las cuatro, ventas no ve compras —`null` en
 * vez de una tarjeta vacía—, y compras no llega ni a la puerta (`RF-08` de la
 * 009). Una pantalla que asume que todos ven todo es una pantalla que se rompe
 * para la mitad de la gente.
 *
 * **Dos ventanas, no una.** La facturación y el catálogo son cortes de un
 * período y cada uno elige el suyo (`RF-05`), por eso cada uno lleva su
 * encabezado con su control. El corte de compras no tiene ninguna: «cuánto
 * debo» y «qué vence esta semana» son preguntas sobre hoy, y ofrecerles un
 * control de fechas sería ofrecer un control que no cambia nada.
 */
export default async function DashboardPage({ searchParams }: PageProps) {
  const filters = await searchParams

  const [sales, catalog, purchases, categories] = await Promise.all([
    fetchFromApi<SalesDashboard>(`/dashboard/sales?${period(filters.desde, filters.hasta)}`),
    fetchFromApi<CatalogDashboard>(
      `/dashboard/catalog?${period(filters.cat_desde, filters.cat_hasta)}`
    ),
    fetchFromApi<PurchasesDashboard>('/dashboard/purchases'),
    fetchFromApi<CategoryList>('/categories'),
  ])

  if (sales === null) {
    return <NoPermission what="el tablero del negocio" isHome />
  }

  const ranOut = (catalog?.stock ?? []).filter(cut => cut.ran_out)

  return (
    <div className="space-y-4">
      <CutHeader
        as="h1"
        title="Cómo venimos"
        since={sales.since}
        until={sales.until}
        whole="Facturación de todo el histórico."
      >
        <PeriodPicker
          label="Período de la facturación"
          fromName="desde"
          toName="hasta"
          from={filters.desde}
          to={filters.hasta}
          keep={{ cat_desde: filters.cat_desde, cat_hasta: filters.cat_hasta }}
        />
      </CutHeader>

      {/*
        La franja va antes que cualquier número de la pantalla, y desde ella se
        llega a los registros que excluyó (`RF-26`): un aviso sin salida es sólo
        una queja.
      */}
      <Excluded howMany={sales.invoiced.excluded} href="/ventas/revision">
        Ninguno de esos registros suma en los números de abajo.
        {sales.invoiced.merged > 0 &&
          ` ${count(sales.invoiced.merged)} ventas repetidas idénticas las unificó el sistema solo.`}
      </Excluded>

      {/*
        La fila de la guía: lo facturado, lo que se debe, lo que vence y lo que
        no llegó. Es `flex` y no una grilla de cuatro columnas fijas porque a
        quien no ve compras le quedan menos tarjetas, y tres huecos vacíos serían
        una pantalla rota en vez de una pantalla más corta.
      */}
      <div className="flex flex-wrap gap-3">
        <InvoicedTile sales={sales} />
        {purchases && <PurchasesTiles purchases={purchases} />}
      </div>

      <div className="grid items-start gap-3 lg:grid-cols-[1.6fr_1fr]">
        <MonthlyBilling months={sales.by_month} excluded={sales.invoiced.excluded}>
          <SalesQuality sales={sales} />
        </MonthlyBilling>
        {categories && <CategorySpendCard categories={categories} />}
      </div>

      {purchases && <UpcomingDues dues={purchases.upcoming} />}

      {catalog && (
        <>
          <CutHeader
            title="Catálogo y precios"
            since={catalog.since}
            until={catalog.until}
            whole="Todo el histórico. Sin fecha de inicio el corte de stock no tiene con qué comparar."
          >
            <PeriodPicker
              label="Período del catálogo"
              fromName="cat_desde"
              toName="cat_hasta"
              from={filters.cat_desde}
              to={filters.cat_hasta}
              keep={{ desde: filters.desde, hasta: filters.hasta }}
            />
          </CutHeader>

          <div className="grid items-start gap-3 lg:grid-cols-[1.6fr_1fr]">
            <PriceCurveCard curve={catalog.price_curve} excluded={catalog.price_curve_excluded} />
            <div className="space-y-3">
              <StockCard
                compared={catalog.stock.length}
                excluded={catalog.stock_excluded}
                ranOut={ranOut.length}
              />
              <NewProductsCard
                howMany={catalog.new_products.length}
                excluded={catalog.new_products_excluded}
              />
            </div>
          </div>

          <RanOutTable cuts={ranOut} />
        </>
      )}
    </div>
  )
}
