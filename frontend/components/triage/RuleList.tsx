'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { revokeRule } from '@/app/actions/triage'
import { Button } from '@/components/ui/button'
import { formatMoment } from '@/lib/catalog/format'
import { caseKindLabel, type Rule } from '@/lib/triage/types'

interface RuleListProps {
  rules: Rule[]
}

/**
 * The decisions the platform is applying on its own (RF-36).
 *
 * Revoking one is destructive in the sense that matters — it gives back the
 * cases that rule was resolving, and undoes what it did (RF-37) — so the button
 * says so before it is pressed.
 */
export function RuleList({ rules }: RuleListProps) {
  const router = useRouter()
  const [working, setWorking] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

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
      <p className="rounded border border-dashed p-6 text-center text-muted-foreground">
        Todavía no hay decisiones guardadas. Cada caso que resuelvas se guarda como regla y se
        aplica sola a los casos iguales.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {error && <p className="text-sm text-red-700">{error}</p>}
      {rules.map(rule => (
        <article
          key={rule.id}
          className="flex flex-wrap items-center justify-between gap-3 rounded border p-3 text-sm"
        >
          <div>
            <p className="font-medium">{caseKindLabel(rule.kind)}</p>
            <p className="text-muted-foreground">
              {JSON.stringify(rule.matcher)} → {JSON.stringify(rule.decision)}
            </p>
            <p className="text-muted-foreground">
              {/* The name is what was stored when the decision was taken. A rule
                  from before that was recorded falls back to the id, which is
                  worse to read but still true. */}
              Decidida por {rule.created_by_name ?? `el usuario #${rule.created_by_user_id}`} el{' '}
              {formatMoment(rule.created_at)}
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
        </article>
      ))}
    </div>
  )
}
