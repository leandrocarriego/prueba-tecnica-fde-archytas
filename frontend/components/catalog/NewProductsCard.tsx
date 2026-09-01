import { Excluded } from '@/components/common/Excluded'
import { count } from '@/lib/format'

interface NewProductsCardProps {
  /** Cuántos productos aparecieron por primera vez en el período (`RF-45`). */
  howMany: number
  /** Cuántos no se pudieron fechar, y por eso no cuentan como nuevos. */
  excluded: number
}

/**
 * Los productos dados de alta en el período (`RF-45`), con la forma de tarjeta
 * de la guía visual (`3b`).
 *
 * Lo excluido primero, el número después: un producto que el portal nunca fechó
 * no es un producto que no existe, es uno que este corte no puede ubicar en el
 * tiempo — y contarlo como «ninguno» sería decidir por él.
 */
export function NewProductsCard({ howMany, excluded }: NewProductsCardProps) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-base font-semibold text-foreground">Productos nuevos</h2>

      <div className="mt-4 space-y-4">
        <Excluded howMany={excluded}>
          No se pudieron fechar dentro del período, así que no se cuentan como nuevos.
        </Excluded>

        <div>
          <div className="amount text-2xl font-medium text-foreground">{count(howMany)}</div>
          <p className="mt-2 text-xs text-muted-foreground">
            aparecieron por primera vez en el período ·{' '}
            {excluded === 0
              ? 'no se excluyó ningún registro'
              : `${count(excluded)} registros excluidos`}
            .
          </p>
        </div>
      </div>
    </section>
  )
}
