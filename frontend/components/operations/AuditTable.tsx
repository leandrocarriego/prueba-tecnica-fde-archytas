import Link from 'next/link'

import { RevertCorrectionButton } from '@/components/catalog/RevertCorrectionButton'
import { datumKey } from '@/lib/catalog/corrections'
// The one place that knows how a date is written is `lib/time`, and this is
// the wrapper over it the rest of the app already uses.
import { formatMoment } from '@/lib/catalog/format'
import { actionLabel, entityHref, entityLabel, fieldLabel, valueText } from '@/lib/operations/audit'
import type { AuditEntry } from '@/lib/operations/types'
import { Empty } from '@/components/ui/state'
import { Code } from '@/components/ui/amount'

/**
 * Which rows get the offer to undo, and which do not.
 *
 * What is undone is the correction standing on a datum, and a datum collects
 * several lines over its life: corrected, undone, corrected again. Keying the
 * offer on the datum alone would put the button on all three of them —
 * including the line that says «Deshizo una corrección» — and all three would
 * undo the same thing, which is the one still standing. That is a button whose
 * row does not describe what pressing it does.
 *
 * So the offer goes on **one** line per datum: the newest that corrected it.
 * The log arrives newest first, so that is the first one seen — and a datum
 * whose latest correction was undone has nothing standing, and gets no offer at
 * all.
 *
 * A page that begins in the middle of a datum's history is the one case left:
 * the newest correction of that datum may be on the page before, and the offer
 * lands on an older line. Pressing it still undoes what the label promises —
 * the correction in force, which is unique per datum — and the alternative,
 * asking the API for one more page to find out, would be a request to decide
 * where a button goes.
 */
function rowsThatOfferTheUndo(
  items: AuditEntry[],
  undoable: Map<string, number>
): Map<number, number> {
  const decided = new Set<string>()
  const offers = new Map<number, number>()
  for (const entry of items) {
    if (entry.action !== 'CORRECTED') continue
    const key = datumKey(entry.entity_type, entry.entity_id, entry.field)
    if (decided.has(key)) continue
    decided.add(key)
    const correctionId = undoable.get(key)
    if (correctionId !== undefined) offers.set(entry.id, correctionId)
  }
  return offers
}

/**
 * The history of manual changes (RF-12, RF-13).
 *
 * A Server Component: it renders and links, and the one interactive thing on it
 * is a Client Component of its own. Every row answers the four questions the
 * feature exists for — who, when, what it said before, and why — and links to
 * the datum itself so its own history is one click away (RF-15).
 *
 * `undoable` is what turns a row into an offer: the correction that still
 * stands on that datum, if the person reading may undo it (RF-30, whose
 * acceptance criterion puts the undo **on this screen**). An empty map is the
 * ordinary case and reads as a log with nothing to undo — which is exactly what
 * it is for everybody but the owner, and for the owner once a correction has
 * already been undone. The screen decides nothing about permissions: it is
 * handed the ids or it is not, and the route refuses anybody else regardless.
 */
export function AuditTable({
  items,
  undoable = new Map<string, number>(),
}: {
  items: AuditEntry[]
  undoable?: Map<string, number>
}) {
  const offers = rowsThatOfferTheUndo(items, undoable)

  if (items.length === 0) {
    return <Empty title="No hay cambios manuales registrados con estos filtros." />
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-card">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-left">
          <tr>
            <th className="p-3 font-medium">Cuándo</th>
            <th className="p-3 font-medium">Quién</th>
            <th className="p-3 font-medium">Qué</th>
            <th className="p-3 font-medium">Decía</th>
            <th className="p-3 font-medium">Quedó</th>
            <th className="p-3 font-medium">Por qué</th>
          </tr>
        </thead>
        <tbody>
          {items.map(entry => {
            const href = entityHref(entry)
            const field = fieldLabel(entry.field)
            const correctionId = offers.get(entry.id)
            return (
              <tr key={entry.id} className="border-t align-top">
                {/* Cuándo pasó algo es un dato que se compara: mono tabular. */}
                <Code
                  value={formatMoment(entry.occurred_at)}
                  cell
                  className="p-3 text-left whitespace-nowrap text-muted-foreground"
                />
                <td className="p-3">{entry.actor_name ?? `Usuario ${entry.actor_user_id}`}</td>
                <td className="p-3">
                  <span className="font-medium">{actionLabel(entry.action)}</span>{' '}
                  {href ? (
                    <Link className="text-link hover:underline" href={href}>
                      {entityLabel(entry.entity_type)} {entry.entity_id}
                    </Link>
                  ) : (
                    <>
                      {entityLabel(entry.entity_type)} {entry.entity_id}
                    </>
                  )}
                  {field && <span className="text-muted-foreground"> · {field}</span>}
                </td>
                {/* Lo que decía y lo que quedó se leen enfrentados: mono, para
                    que dos valores parecidos se distingan de un vistazo. */}
                <Code
                  value={valueText(entry.old_value)}
                  cell
                  className="p-3 text-left text-muted-foreground"
                />
                <Code
                  value={valueText(entry.new_value)}
                  cell
                  className="p-3 text-left font-medium"
                />
                <td className="p-3">
                  {entry.reason_label ?? '—'}
                  {entry.reason_detail && (
                    <span className="block text-muted-foreground">{entry.reason_detail}</span>
                  )}
                  {correctionId !== undefined && (
                    <span className="mt-1 block">
                      <RevertCorrectionButton correctionId={correctionId} />
                    </span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
