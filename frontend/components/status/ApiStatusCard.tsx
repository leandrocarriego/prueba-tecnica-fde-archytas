'use client'

import * as React from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import type { HealthProbe } from '@/lib/health'

/** How often the card re-asks on its own, in milliseconds. */
const REFRESH_MS = 15_000

type Tone = 'ok' | 'degraded' | 'unreachable'

/**
 * Full class strings, never composed at runtime: Tailwind scans the source as
 * text, so a template literal like `bg-${tone}-500` produces no CSS at all.
 */
const TONE_STYLES: Record<Tone, { dot: string; halo: string; label: string }> = {
  ok: {
    dot: 'bg-emerald-500',
    halo: 'bg-emerald-500/20',
    label: 'text-emerald-600 dark:text-emerald-400',
  },
  degraded: {
    dot: 'bg-amber-500',
    halo: 'bg-amber-500/20',
    label: 'text-amber-600 dark:text-amber-400',
  },
  unreachable: {
    dot: 'bg-red-500',
    halo: 'bg-red-500/20',
    label: 'text-red-600 dark:text-red-400',
  },
}

type StatusView = {
  tone: Tone
  headline: string
  explanation: string
  facts: { label: string; value: string }[]
}

/** Turn a probe into what the card shows. All copy is user-facing, so Spanish. */
function describe(probe: HealthProbe): StatusView {
  if (!probe.reachable) {
    return {
      tone: 'unreachable',
      headline: 'Sin respuesta',
      explanation: probe.reason,
      facts: [],
    }
  }

  const { report, httpStatus } = probe
  // `report.database.detail` is not rendered on purpose: the backend writes it
  // in English, and it is deliberately generic so as not to leak hostnames or
  // drivers — so it says nothing this label does not already say, in a language
  // this audience does not read (Artículo VIII).
  const facts = [
    { label: 'Servicio', value: report.service },
    { label: 'Entorno', value: report.environment },
    { label: 'Base de datos', value: report.database.status === 'ok' ? 'Responde' : 'No responde' },
    { label: 'Respuesta HTTP', value: String(httpStatus) },
  ]

  if (report.status === 'ok') {
    return {
      tone: 'ok',
      headline: 'Operativa',
      explanation: 'La API responde y sus dependencias también.',
      facts,
    }
  }

  return {
    tone: 'degraded',
    headline: 'Con problemas',
    explanation: 'La API responde, pero alguna de sus dependencias no está disponible.',
    facts,
  }
}

const TIME_FORMAT = new Intl.DateTimeFormat('es-AR', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
})

export function ApiStatusCard({ initial }: { initial: HealthProbe }) {
  const [probe, setProbe] = React.useState<HealthProbe>(initial)
  const [checkedAt, setCheckedAt] = React.useState<Date | null>(null)
  const [checking, setChecking] = React.useState(false)

  const check = React.useCallback(async () => {
    setChecking(true)
    try {
      const response = await fetch('/api/health', { cache: 'no-store' })
      setProbe((await response.json()) as HealthProbe)
    } catch {
      // The page itself could not reach its own route handler — almost always
      // the visitor's connection, not the API.
      setProbe({ reachable: false, reason: 'Se perdió la conexión con la aplicación.' })
    } finally {
      setCheckedAt(new Date())
      setChecking(false)
    }
  }, [])

  // The server already rendered a probe. Stamping its time here, after mount,
  // instead of passing it down keeps the server and client markup identical —
  // a clock rendered on both sides is a guaranteed hydration mismatch.
  React.useEffect(() => {
    setCheckedAt(new Date())
  }, [])

  React.useEffect(() => {
    const timer = setInterval(check, REFRESH_MS)
    return () => clearInterval(timer)
  }, [check])

  // Coming back to a background tab should not show a status from ten minutes
  // ago while the interval waits for its next tick.
  React.useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible') void check()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [check])

  const view = describe(probe)
  const tone = TONE_STYLES[view.tone]

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Estado del servicio</CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        <div className="flex items-start gap-3" role="status" aria-live="polite">
          <span className="relative mt-1.5 flex size-3 shrink-0">
            <span
              className={`absolute inline-flex size-full animate-ping rounded-full ${tone.halo}`}
            />
            <span className={`relative inline-flex size-3 rounded-full ${tone.dot}`} />
          </span>
          <div className="space-y-1">
            <p className={`text-xl font-semibold leading-none ${tone.label}`}>{view.headline}</p>
            <p className="text-sm text-muted-foreground">{view.explanation}</p>
          </div>
        </div>

        {view.facts.length > 0 && (
          <dl className="divide-y divide-border border-t border-border text-sm">
            {view.facts.map(fact => (
              <div key={fact.label} className="flex items-baseline justify-between gap-4 py-2">
                <dt className="text-muted-foreground">{fact.label}</dt>
                <dd className="text-right font-medium">{fact.value}</dd>
              </div>
            ))}
          </dl>
        )}
      </CardContent>

      <CardFooter className="justify-between gap-4">
        <p className="text-xs text-muted-foreground">
          {checkedAt ? `Última comprobación: ${TIME_FORMAT.format(checkedAt)}` : 'Comprobando…'}
        </p>
        <Button variant="outline" size="sm" onClick={() => void check()} disabled={checking}>
          {checking ? 'Comprobando…' : 'Reintentar'}
        </Button>
      </CardFooter>
    </Card>
  )
}
