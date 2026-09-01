import { CategorySpendCard } from '@/components/catalog/CategorySpendCard'
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
import type { SalesDashboard } from '@/lib/sales/types'

export const metadata = {
  title: 'Tablero — Plataforma Cordillera',
}

interface PageProps {
  searchParams: Promise<{
    desde?: string
    hasta?: string
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
 * franja de lo que quedó afuera, y recién después los números. Primero se dice
 * si se puede confiar en los datos, después se muestran (`RF-07`, `RF-14`); y lo
 * excluido va pegado a cada número, no al pie, porque `RF-25` pide que cada
 * indicador informe cuántos registros dejó afuera y `RF-27` que lo diga incluso
 * cuando no dejó ninguno: «cero excluidos» es una respuesta, y un silencio no.
 *
 * **Tres consultas, y cada una puede faltar sin llevarse la pantalla.** Son tres
 * secciones distintas del sistema de accesos, así que quién entra decide cuánto
 * tablero hay: el dueño ve las tres, ventas no ve compras —`null` en vez de una
 * tarjeta vacía— y compras no llega ni a la puerta (`RF-08` de la 009). Una
 * pantalla que asume que todos ven todo es una pantalla que se rompe para la
 * mitad de la gente.
 *
 * **Un solo período, el de la facturación.** El corte de compras no lleva
 * control de fechas porque «cuánto debo» y «qué vence esta semana» son preguntas
 * sobre hoy, y ofrecerles un selector sería ofrecer un control que no cambia
 * nada.
 *
 * **El corte del catálogo se sacó de acá por pedido del dueño** (2026-09-01): la
 * curva de precio promedio, el corte de stock, los productos nuevos y los que se
 * quedaron sin stock. No se movieron a otra pantalla ni se escondieron detrás de
 * un permiso: se sacaron. El tablero contesta cómo viene el negocio, y el estado
 * del catálogo es una pregunta de `/precios`.
 */
export default async function DashboardPage({ searchParams }: PageProps) {
  const filters = await searchParams

  const [sales, purchases, categories] = await Promise.all([
    fetchFromApi<SalesDashboard>(`/dashboard/sales?${period(filters.desde, filters.hasta)}`),
    fetchFromApi<PurchasesDashboard>('/dashboard/purchases'),
    fetchFromApi<CategoryList>('/categories'),
  ])

  if (sales === null) {
    return <NoPermission what="el tablero del negocio" isHome />
  }

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
        />
      </CutHeader>

      {/*
        La franja va antes que cualquier número de la pantalla, y desde ella se
        llega a los registros que excluyó (`RF-26`): un aviso sin salida es sólo
        una queja.

        **Dice de qué está hecho el número**, y no sólo cuánto vale, porque las
        dos mitades no se resuelven en el mismo lugar y una de ellas no se
        resuelve en ninguno: lo que el sistema unificó solo ya está decidido, y
        lo que una persona descartó también. Sin esa aclaración el aviso promete
        «ver cuáles» sobre noventa y seis registros y la cola muestra trece, que
        es lo único que efectivamente espera a alguien.
      */}
      <Excluded howMany={sales.invoiced.excluded} href="/revision?area=SALES">
        Ninguno de esos registros suma en los números de abajo.
        {sales.invoiced.merged > 0 &&
          ` ${count(sales.invoiced.merged)} son ventas repetidas idénticas que el sistema unificó solo.`}
        {sales.pending_decisions > 0
          ? ` ${count(sales.pending_decisions)} ${sales.pending_decisions === 1 ? 'espera una decisión' : 'esperan una decisión'}; el resto ya se decidió.`
          : ' Ninguno espera una decisión: todos ya se decidieron.'}
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
    </div>
  )
}
