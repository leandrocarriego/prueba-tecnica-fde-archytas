import Link from 'next/link'

import { Share } from '@/components/common/Share'
import { Money } from '@/components/ui/amount'
import { count } from '@/lib/format'
import type { CategoryList } from '@/lib/catalog/types'

/** Cuántos rubros entran antes de que el panel deje de leerse de un vistazo. */
const SHOWN = 5

/**
 * De qué lado del negocio habla el panel, y con qué palabras.
 *
 * Las dos mitades son la misma tarjeta con otra columna: un total repartido por
 * rubro, con lo no atribuido rayado y visible. Lo que cambia es de dónde sale la
 * plata, y eso hay que decirlo — un panel que dice «por rubro» sin decir de qué
 * está hablando es el que hacía que el tablero de quien vende contestara cuánto
 * se compró.
 */
interface Side {
  title: string
  /** De dónde salen los números, dicho en una línea bajo el título. */
  source: string
  /** Qué se lee cuando todavía no hay nada que repartir. */
  empty: string
  /** El pie, después del importe: «… en órdenes», «… vendidos». */
  over: string
  amountOf: (item: CategoryList['items'][number]) => string
  totalOf: (list: CategoryList) => string
  unclassifiedOf: (list: CategoryList) => string
}

const SPEND: Side = {
  title: 'Gasto por rubro',
  source: 'Sale de las órdenes de compra, con el rubro del producto que pedían.',
  empty: 'Todavía no hay órdenes de compra con importe para repartir por rubro.',
  over: 'en órdenes.',
  amountOf: item => item.spend,
  totalOf: list => list.spend_total,
  unclassifiedOf: list => list.spend_unclassified,
}

const REVENUE: Side = {
  title: 'Ventas por rubro',
  source: 'Sale de las ventas registradas, con el rubro del producto vendido.',
  empty: 'Todavía no hay ventas con importe para repartir por rubro.',
  over: 'vendidos.',
  amountOf: item => item.revenue,
  totalOf: list => list.revenue_total,
  unclassifiedOf: list => list.revenue_unclassified,
}

/**
 * En qué se gastó, por rubro (guía visual `3b`).
 *
 * **Sale de las órdenes de compra**, y el panel lo dice: es la plata que el
 * portal imprimió en cada orden, sumada por el rubro del producto que la orden
 * pedía. No es una repartija de un total por estimación, que es lo que un
 * gráfico de torta suele esconder.
 */
export function CategorySpendCard({ categories }: { categories: CategoryList }) {
  return <CategoryBreakdown categories={categories} side={SPEND} />
}

/**
 * Lo que se vendió, por rubro.
 *
 * El mismo panel por el otro lado, y existe porque el tablero de quien vende
 * mostraba el de arriba: una respuesta sobre lo que se compra, puesta delante de
 * la persona cuyo trabajo es vender. El dato no se podía calcular hasta ahora —
 * la venta sabe su producto y el producto sabe su rubro, pero viven en dos
 * módulos que no se leen entre sí—, así que el catálogo mantiene su propia
 * proyección de lo vendido, alimentada por eventos.
 */
export function CategoryRevenueCard({ categories }: { categories: CategoryList }) {
  return <CategoryBreakdown categories={categories} side={REVENUE} />
}

/**
 * El panel, sin saber de qué lado del negocio habla.
 *
 * «Sin rubro asignado» es un renglón más y va rayado: es plata real que existe
 * y que **no está atribuida** —un producto sin rubro, o un código que no está en
 * el catálogo—. Esconderlo haría que los porcentajes cerraran mintiendo, y es
 * además lo único de este panel sobre lo que se puede hacer algo: por eso lleva
 * la salida a asignarlos.
 */
function CategoryBreakdown({ categories, side }: { categories: CategoryList; side: Side }) {
  const total = Number(side.totalOf(categories))
  const unclassified = Number(side.unclassifiedOf(categories))
  const ranked = [...categories.items]
    .filter(item => Number(side.amountOf(item)) > 0)
    .sort((first, second) => Number(side.amountOf(second)) - Number(side.amountOf(first)))
    .slice(0, SHOWN)

  return (
    <section className="flex flex-col rounded-xl border border-border bg-card p-5">
      <h2 className="text-base font-semibold text-foreground">{side.title}</h2>
      <p className="mt-1 text-xs text-muted-foreground">{side.source}</p>

      {total <= 0 ? (
        <p className="mt-5 text-sm text-muted-foreground">{side.empty}</p>
      ) : (
        <div className="mt-5 space-y-3">
          {ranked.map(item => (
            <Share
              key={item.id}
              label={item.name}
              reading={
                <Reading
                  amount={side.amountOf(item)}
                  pct={percent(Number(side.amountOf(item)), total)}
                />
              }
              share={(Number(side.amountOf(item)) / total) * 100}
            />
          ))}
          {unclassified > 0 && (
            <Share
              label="Sin rubro asignado"
              reading={
                <Reading
                  amount={side.unclassifiedOf(categories)}
                  pct={percent(unclassified, total)}
                />
              }
              share={(unclassified / total) * 100}
              excluded
            />
          )}
        </div>
      )}

      <p className="mt-4 text-xs text-muted-foreground">
        {/*
          El importe sale con `<Money>` aunque esté en un pie: el total es plata,
          y `UI-04` no hace excepciones por tamaño de letra.
        */}
        Sobre <Money value={side.totalOf(categories)} as="span" /> {side.over}
      </p>

      {categories.unclassified_count > 0 && (
        <Link
          className="mt-auto pt-3 text-[13px] font-semibold text-link hover:underline"
          href="/rubros/sin-clasificar"
        >
          Normalizar {count(categories.unclassified_count)} productos →
        </Link>
      )}
    </section>
  )
}

/**
 * Lo que se lee a la derecha de cada barra: **cuánta plata, y qué porción**.
 *
 * El porcentaje solo no alcanza. «Herramientas 35 %» no se puede llevar a una
 * conversación con el proveedor ni comparar con nada: para saber de cuánto se
 * está hablando había que ir hasta el pie de la tarjeta, leer el total y hacer
 * la cuenta. El importe va primero porque es la pregunta —cuánto hay acá— y la
 * porción atrás, que es el contexto.
 */
function Reading({ amount, pct }: { amount: string; pct: number }) {
  return (
    <>
      <Money value={amount} as="span" />
      <span className="ml-1.5 text-muted-foreground">{pct} %</span>
    </>
  )
}

/** El porcentaje entero de una parte, que es como la guía lo escribe. */
function percent(part: number, whole: number): number {
  return Math.round((part / whole) * 100)
}
