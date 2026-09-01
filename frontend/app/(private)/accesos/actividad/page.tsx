import { getSession } from '@/app/actions/auth'
import { listAccessEvents } from '@/app/actions/access'
import { NoPermission } from '@/components/common/NoPermission'
import { Code } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Empty } from '@/components/ui/state'
import { canSee } from '@/lib/auth/permissions'
import { SHORT_MOMENT_FORMAT } from '@/lib/time'
import type { BadgeTone } from '@/lib/ui/tone'

/** What each kind of event is called on screen, in the owner's words. */
const EVENT_LABELS: Record<string, { label: string; tone: BadgeTone }> = {
  LOGIN_SUCCEEDED: { label: 'Entró', tone: 'ok' },
  LOGIN_REJECTED: { label: 'No pudo entrar', tone: 'warn' },
  ACCESS_LOCKED: { label: 'Acceso bloqueado', tone: 'danger' },
  PERMISSION_DENIED: { label: 'Quiso ver algo que no le toca', tone: 'danger' },
  ACCESS_GRANTED: { label: 'Alta de acceso', tone: 'info' },
  ACCESS_ROLE_CHANGED: { label: 'Cambio de rol', tone: 'info' },
  ACCESS_DEACTIVATED: { label: 'Acceso desactivado', tone: 'neutral' },
  ACCESS_REACTIVATED: { label: 'Acceso reactivado', tone: 'info' },
}

// Shorter than `formatMoment` in lib/catalog/format on purpose: this table
// has one row per event and the seconds push everything else off the line.
function shortMoment(iso: string): string {
  return SHORT_MOMENT_FORMAT.format(new Date(iso))
}

/**
 * The record of who came in and who was turned away (RF-30).
 *
 * One list and not two: a login, a refusal and the owner handing out an access
 * are the same question with a different verb — who did what to which access,
 * and when — and they are read together.
 */
export default async function ActivityPage() {
  const session = await getSession()
  if (!session || !canSee(session.permissions, 'ACCESS_LOG')) {
    return <NoPermission what="el registro de actividad" />
  }

  const log = await listAccessEvents()
  if (!log) {
    return <NoPermission what="el registro de actividad" />
  }

  const names = new Map<number, string>()
  const accesses = await import('@/app/actions/access').then(module => module.listAccesses())
  accesses?.items.forEach(item => names.set(item.id, item.name))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Actividad</h1>
        <p className="text-muted-foreground">
          Quién entró, a quién se le negó el paso, y qué cambió en los accesos.
        </p>
      </div>

      {log.items.length === 0 ? (
        <Empty title="Todavía no hay nada registrado." />
      ) : (
        <table className="w-full text-left text-sm">
          <thead className="border-b text-muted-foreground">
            <tr>
              <th className="py-2">Cuándo</th>
              <th>Qué pasó</th>
              <th>Quién</th>
              <th>Detalle</th>
            </tr>
          </thead>
          <tbody>
            {log.items.map(event => {
              const label = EVENT_LABELS[event.kind] ?? {
                label: event.kind,
                tone: 'neutral' as BadgeTone,
              }
              return (
                <tr key={event.id} className="border-b last:border-0 align-top">
                  <Code
                    value={shortMoment(event.occurred_at)}
                    cell
                    className="py-3 text-left whitespace-nowrap"
                  />
                  <td>
                    <Badge tone={label.tone}>{label.label}</Badge>
                  </td>
                  <td>
                    {event.user_id
                      ? (names.get(event.user_id) ?? `Acceso ${event.user_id}`)
                      : // No account matched: the attempt is kept anyway, and
                        // the address that was tried is what identifies it.
                        (event.attempted_email ?? '—')}
                  </td>
                  <td className="text-muted-foreground">{event.resource ?? '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
