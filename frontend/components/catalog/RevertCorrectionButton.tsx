'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { revertCorrection } from '@/app/actions/corrections'
import { useToast } from '@/components/ui/toast'

/**
 * Undo a correction and give the datum back the portal's value (RF-30, RF-31).
 *
 * It is only ever rendered where there **is** a correction to undo, which is
 * what RF-33 asks for: a datum loaded entirely by hand has no correction, so
 * this offer never appears over it. The backend refuses anybody but the owner,
 * and says so here if somebody else gets this far.
 *
 * How it went is read in two different places (RF-22), and that is not an
 * inconsistency with `CorrectionDialog`: it is the same rule that dialog
 * follows — the verdict has to be rendered by something that outlives the run
 * that wrote it. What differs is what the run takes away, and that is the half
 * no test can read off the source: that dialog only closes, and this button is
 * gone.
 *
 * A refusal leaves this button exactly where it was, so its message goes right
 * beside it, over the correction that was not undone. There is one of these per
 * standing correction, so a message off in the corner of the screen would not
 * say which one failed.
 *
 * Undoing it takes the button away. The correction stops being in force, the
 * refreshed page no longer lists it, and this component is unmounted along with
 * anything it had written in its own state. So the confirmation is announced to
 * the toaster in the root layout, which is the only thing still on screen once
 * the row is gone. Writing it into local state — the shape `CorrectionDialog`
 * can afford, because it is rendered whether or not there is anything left to
 * correct — would be this same defect again: a message written where nobody
 * will be around to read it.
 */
export function RevertCorrectionButton({ correctionId }: { correctionId: number }) {
  const router = useRouter()
  const { addToast } = useToast()
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
    addToast({
      type: 'success',
      title: 'Corrección deshecha',
      description: 'El dato vuelve a mostrar el valor que informó el portal.',
    })
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
