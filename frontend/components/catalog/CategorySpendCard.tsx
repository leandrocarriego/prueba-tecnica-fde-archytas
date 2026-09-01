import Link from 'next/link'

import { Share } from '@/components/common/Share'
import { Money } from '@/components/ui/amount'
import { count } from '@/lib/format'
import type { CategoryList } from '@/lib/catalog/types'

/** Cuántos rubros entran antes de que el panel deje de leerse de un vistazo. */
const SHOWN = 5

/**
 * En qué se gastó, por rubro (guía visual `3b`).
 *
 * **Sale de las órdenes de compra**, y el panel lo dice: es la plata que el
 * portal imprimió en cada orden, sumada por el rubro del producto que la orden
 * pedía. No es una repartija de un total por estimación, que es lo que un
 * gráfico de torta suele esconder.
 *
 * «Sin rubro asignado» es un renglón más y va rayado: es gasto real que existe
 * y que **no está atribuido** —una orden de un producto sin rubro, o de un
 * código que no está en el catálogo—. Esconderlo haría que los porcentajes
 * cerraran mintiendo, y es además lo único de este panel sobre lo que se puede
 * hacer algo: por eso lleva la salida a asignarlos.
 */
export function CategorySpendCard({ categories }: { categories: CategoryList }) {
  const total = Number(categories.spend_total)
  const unclassified = Number(categories.spend_unclassified)
  const ranked = [...categories.items]
    .filter(item => Number(item.spend) > 0)
    .sort((first, second) => Number(second.spend) - Number(first.spend))
    .slice(0, SHOWN)

  return (
    <section className="flex flex-col rounded-xl border border-border bg-card p-5">
      <h2 className="text-base font-semibold text-foreground">Gasto por rubro</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Sale de las órdenes de compra, con el rubro del producto que pedían.
      </p>

      {total <= 0 ? (
        <p className="mt-5 text-sm text-muted-foreground">
          Todavía no hay órdenes de compra con importe para repartir por rubro.
        </p>
      ) : (
        <div className="mt-5 space-y-3">
          {ranked.map(item => (
            <Share
              key={item.id}
              label={item.name}
              reading={<Reading amount={item.spend} pct={percent(Number(item.spend), total)} />}
              share={(Number(item.spend) / total) * 100}
            />
          ))}
          {unclassified > 0 && (
            <Share
              label="Sin rubro asignado"
              reading={
                <Reading
                  amount={categories.spend_unclassified}
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
        Sobre <Money value={categories.spend_total} as="span" /> en órdenes.
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
 * la cuenta. El importe va primero porque es la pregunta —cuánto gasté acá— y
 * la porción atrás, que es el contexto.
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
