'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { readPriceUpdate, requestPriceUpdate } from '@/app/actions/prices'
import { Button } from '@/components/ui/button'

/** How often the screen asks how the run it started is going. */
const POLL_MS = 2_000
/** Long enough for a portal visit, short enough not to hang forever on screen. */
const MAX_POLLS = 60

type Outcome = { tone: 'ok' | 'error' | 'info'; message: string }

const TONES: Record<Outcome['tone'], string> = {
  ok: 'text-ok',
  error: 'text-danger',
  info: 'text-muted-foreground',
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * "Traer la lista ahora" (RF-14), and what happened afterwards (RF-16).
 *
 * A Client Component because it is a button with state: it asks for the run,
 * then follows **that run by its id** until it ends. Not `/price-updates/status`
 * — that one reports the last *successful* update, so a run that failed would
 * never show up there and whoever asked would never learn that it failed.
 */
export function UpdateNowButton() {
  const router = useRouter()
  const [running, setRunning] = useState(false)
  const [outcome, setOutcome] = useState<Outcome | null>(null)

  async function follow(jobRunId: number): Promise<Outcome> {
    for (let attempt = 0; attempt < MAX_POLLS; attempt += 1) {
      await sleep(POLL_MS)
      const run = await readPriceUpdate(jobRunId)
      if (!run.ok) return { tone: 'error', message: run.message }
      if (run.data.status === 'SUCCEEDED') {
        return { tone: 'ok', message: 'Listo: se trajo la lista del portal.' }
      }
      if (run.data.status === 'FAILED') {
        return {
          tone: 'error',
          message: `La consulta falló: ${run.data.error ?? 'sin detalle'}`,
        }
      }
    }
    return {
      tone: 'info',
      message: 'La consulta sigue en curso. Podés seguir trabajando y volver en un rato.',
    }
  }

  async function onClick() {
    setRunning(true)
    setOutcome({ tone: 'info', message: 'Consultando el portal…' })

    const requested = await requestPriceUpdate()
    if (!requested.ok) {
      setOutcome({ tone: 'error', message: requested.message })
      setRunning(false)
      return
    }

    setOutcome(await follow(requested.data.job_run_id))
    setRunning(false)
    router.refresh()
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button onClick={onClick} disabled={running}>
        {running ? 'Trayendo la lista…' : 'Actualizar ahora'}
      </Button>
      {outcome && <p className={`text-sm ${TONES[outcome.tone]}`}>{outcome.message}</p>}
    </div>
  )
}
