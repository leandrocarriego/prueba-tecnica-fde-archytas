'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { revertCorrection } from '@/app/actions/corrections'

/**
 * Undo a correction and give the datum back the portal's value (RF-30, RF-31).
 *
 * It is only ever rendered where there **is** a correction to undo, which is
 * what RF-33 asks for: a datum loaded entirely by hand has no correction, so
 * this offer never appears over it. The backend refuses anybody but the owner,
 * and says so here if somebody else gets this far.
 */
export function RevertCorrectionButton({ correctionId }: { correctionId: number }) {
  const router = useRouter()
  const [working, setWorking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onClick() {
    setWorking(true)
    setError(null)
    const result = await revertCorrection(correctionId)
    setWorking(false)
    if (!result.ok) {
      setError(result.message)
      return
    }
    router.refresh()
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <button
        className="cursor-pointer text-sm underline underline-offset-2 disabled:opacity-50"
        disabled={working}
        onClick={onClick}
        type="button"
      >
        {working ? 'Deshaciendo…' : 'Volver al valor del portal'}
      </button>
      {error && <span className="text-sm text-red-700">{error}</span>}
    </span>
  )
}
