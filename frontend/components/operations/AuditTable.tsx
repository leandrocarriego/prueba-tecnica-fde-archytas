import Link from 'next/link'

// The one place that knows how a date is written is `lib/time`, and this is
// the wrapper over it the rest of the app already uses.
import { formatMoment } from '@/lib/catalog/format'
import { actionLabel, entityHref, entityLabel, fieldLabel, valueText } from '@/lib/operations/audit'
import type { AuditEntry } from '@/lib/operations/types'

/**
 * The history of manual changes (RF-12, RF-13).
 *
 * A Server Component: it renders and links, and nothing on it is interactive.
 * Every row answers the four questions the feature exists for — who, when, what
 * it said before, and why — and links to the datum itself so its own history is
 * one click away (RF-15).
 */
export function AuditTable({ items }: { items: AuditEntry[] }) {
  if (items.length === 0) {
    return (
      <p className="rounded border border-dashed p-8 text-center text-muted-foreground">
        No hay cambios manuales registrados con estos filtros.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded border">
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
            return (
              <tr key={entry.id} className="border-t align-top">
                <td className="p-3 whitespace-nowrap text-muted-foreground">
                  {formatMoment(entry.occurred_at)}
                </td>
                <td className="p-3">{entry.actor_name ?? `Usuario ${entry.actor_user_id}`}</td>
                <td className="p-3">
                  <span className="font-medium">{actionLabel(entry.action)}</span>{' '}
                  {href ? (
                    <Link className="underline underline-offset-2" href={href}>
                      {entityLabel(entry.entity_type)} {entry.entity_id}
                    </Link>
                  ) : (
                    <>
                      {entityLabel(entry.entity_type)} {entry.entity_id}
                    </>
                  )}
                  {field && <span className="text-muted-foreground"> · {field}</span>}
                </td>
                <td className="p-3 text-muted-foreground">{valueText(entry.old_value)}</td>
                <td className="p-3 font-medium">{valueText(entry.new_value)}</td>
                <td className="p-3">
                  {entry.reason_label ?? '—'}
                  {entry.reason_detail && (
                    <span className="block text-muted-foreground">{entry.reason_detail}</span>
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
