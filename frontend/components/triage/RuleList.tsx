'use client'

import { useState, type ReactNode } from 'react'
import { useRouter } from 'next/navigation'

import { revokeRule } from '@/app/actions/triage'
import { Code, Money } from '@/components/ui/amount'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Notice } from '@/components/ui/notice'
import { Empty } from '@/components/ui/state'
import { formatDay, formatMoment } from '@/lib/catalog/format'
import type { Category } from '@/lib/catalog/types'
import { caseKindLabel, type Rule } from '@/lib/triage/types'

interface RuleListProps {
  rules: Rule[]
  /** Para poder nombrar el rubro de una regla en vez de mostrar su número. */
  categories: Category[]
}

/**
 * The decisions the platform is applying on its own (RF-36).
 *
 * Revoking one is destructive in the sense that matters — it gives back the
 * cases that rule was resolving, and undoes what it did (RF-37) — so the button
 * says so before it is pressed.
 *
 * **Cada regla se lee como una frase, y ésa es la corrección.** Esta lista
 * mostraba el `matcher` y la `decision` con un `JSON.stringify` cada uno, así
 * que decía `{"kind":"unknown_category","category_text":"Seg. Industrial"} →
 * {"category_id":7}`. Quien viene a esta pantalla viene a decidir si deja algo
 * sin efecto, y para eso tiene que entender qué hace: un volcado de JSON con el
 * número de un rubro adentro no se lo dice a nadie que no tenga la tabla de
 * rubros en la cabeza.
 *
 * Las dos mitades son las que el modelo ya tenía —**cuándo** se aplica y **qué
 * hace**—, sólo que dichas en castellano. El `kind` deja de repetirse en la
 * frase porque ya está arriba, en el título de la tarjeta.
 */
export function RuleList({ rules, categories }: RuleListProps) {
  const router = useRouter()
  const [working, setWorking] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const names = new Map(categories.map(category => [category.id, category.name]))

  async function revoke(ruleId: number) {
    setWorking(ruleId)
    setError(null)
    const result = await revokeRule(ruleId)
    setWorking(null)
    if (result.ok) {
      router.refresh()
      return
    }
    setError(result.message)
  }

  if (rules.length === 0) {
    return (
      <Empty title="Todavía no hay decisiones guardadas.">
        Cada caso que resuelvas se guarda como regla y se aplica sola a los casos iguales.
      </Empty>
    )
  }

  return (
    <div className="space-y-2">
      {error && <Notice tone="danger" title={error} />}
      {rules.map(rule => (
        <Card
          key={rule.id}
          className="flex flex-wrap items-center justify-between gap-3 p-4 text-sm"
        >
          <div className="space-y-0.5">
            <p className="font-medium">{caseKindLabel(rule.kind)}</p>
            <p className="text-muted-foreground">
              {conditionOf(rule)}, {outcomeOf(rule, names)}.
            </p>
            {/* La hora exacta queda en el `title`: para decidir si una regla se
                deja sin efecto alcanza el día, y los segundos son ruido. */}
            <p className="text-xs text-muted-foreground" title={formatMoment(rule.created_at)}>
              {authorshipOf(rule)}
            </p>
          </div>
          <Button
            variant="outline"
            disabled={working === rule.id}
            onClick={() => revoke(rule.id)}
            title="Los casos que esta regla venía resolviendo vuelven a revisión"
          >
            {working === rule.id ? 'Anulando…' : 'Dejar sin efecto'}
          </Button>
        </Card>
      ))}
    </div>
  )
}

/**
 * Qué tiene que volver a pasar para que la regla conteste sola.
 *
 * Es el `matcher`, que trae siempre el `kind` y además la única cosa por la que
 * se reconoce el caso: la forma escrita cuando es un rubro, el código del
 * producto en todo lo demás. El `kind` no se dice acá porque es el título de la
 * tarjeta, y repetirlo alargaría la frase sin agregarle nada.
 */
function conditionOf(rule: Rule): ReactNode {
  const matcher = rule.matcher

  const text = matcher.category_text
  if (typeof text === 'string' && text !== '') {
    return (
      <>
        Cuando el rubro llegue escrito <Code value={text} />
      </>
    )
  }

  const code = matcher.product_code
  if (typeof code === 'string' && code !== '') {
    return (
      <>
        Cuando vuelva a llegar el producto <Code value={code} />
      </>
    )
  }

  // Un caso sin código ni forma escrita se reconoce por el producto, y el
  // número es lo único que hay: decir «ese mismo producto» sería más lindo y
  // no diría cuál.
  const id = matcher.product_id
  if (typeof id === 'number') {
    return (
      <>
        Cuando vuelva a llegar el producto <Code value={`#${id}`} />
      </>
    )
  }

  return <>Cuando vuelva a pasar lo mismo</>
}

/**
 * Qué hace la plataforma cuando eso pasa.
 *
 * Las decisiones son libres por diseño —la cola es genérica— así que esto
 * reconoce las que el producto sabe tomar y **muestra el resto tal cual**. Una
 * forma que no se reconozca sale como llegó: esconderla dejaría una regla en
 * vigencia de la que la pantalla no dice qué hace, que es peor que un JSON.
 */
function outcomeOf(rule: Rule, names: Map<number, string>): ReactNode {
  const decision = rule.decision

  const categoryId = decision.category_id
  if (typeof categoryId === 'number') {
    const name = names.get(categoryId)
    // Un rubro que ya no está en la lista deja su número, que es lo único que
    // queda de él. Mono, porque es un número que se compara y no una palabra.
    return name === undefined ? (
      <>
        lo clasifica en el rubro <Code value={`#${categoryId}`} />
      </>
    ) : (
      <>
        lo clasifica en <span className="font-medium text-foreground">{name}</span>
      </>
    )
  }

  const price = decision.price
  if (typeof price === 'string' || typeof price === 'number') {
    return (
      <>
        le registra el precio <Money value={price} />
      </>
    )
  }

  switch (decision.action) {
    case 'incorporate':
      return <>lo incorpora al catálogo</>
    case 'discontinue':
      return <>lo da por discontinuado</>
    case 'keep':
      return <>lo mantiene vigente</>
    case 'ignore':
      // La misma decisión quiere decir dos cosas distintas, y por eso mira el
      // caso: dejar un producto afuera del catálogo no es dar por revisada una
      // fila que nadie pudo leer.
      return rule.kind === 'unknown_product' ? (
        <>lo deja fuera del catálogo</>
      ) : (
        <>lo da por revisado</>
      )
  }

  return (
    <>
      la resuelve así: <Code value={JSON.stringify(decision)} />
    </>
  )
}

/**
 * Quién la decidió y cuándo (RF-32).
 *
 * Una regla que vino sembrada en la puesta en marcha no tiene autor —la
 * migración la inserta con `created_by_user_id` en `NULL`— y decir «Decidida
 * por Sembrado en la puesta en marcha» no es una frase. El nombre guardado se
 * muestra tal cual, porque es el dato; lo que cambia es cómo se lo presenta.
 */
function authorshipOf(rule: Rule): string {
  const who =
    rule.created_by_user_id === null
      ? (rule.created_by_name ?? 'Vino con el sistema')
      : `Decidida por ${rule.created_by_name ?? `el usuario #${rule.created_by_user_id}`}`
  const corrected = rule.updated_at ? ` · corregida el ${formatDay(rule.updated_at)}` : ''
  return `${who} · ${formatDay(rule.created_at)}${corrected}`
}
