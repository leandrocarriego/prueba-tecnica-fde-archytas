import { getSession } from '@/app/actions/auth'
import { listAccessEvents } from '@/app/actions/access'
import { NoPermission } from '@/components/common/NoPermission'
import { canSee } from '@/lib/auth/permissions'
import { SHORT_MOMENT_FORMAT } from '@/lib/time'

/** What each kind of event is called on screen, in the owner's words. */
const EVENT_LABELS: Record<string, { label: string; tone: string }> = {
  LOGIN_SUCCEEDED: { label: 'Entró', tone: 'pill pill-ok' },
  LOGIN_REJECTED: { label: 'No pudo entrar', tone: 'pill pill-warn' },
  ACCESS_LOCKED: { label: 'Acceso bloqueado', tone: 'pill pill-danger' },
  PERMISSION_DENIED: { label: 'Quiso ver algo que no le toca', tone: 'pill pill-danger' },
  ACCESS_GRANTED: { label: 'Alta de acceso', tone: 'pill pill-info' },
  ACCESS_ROLE_CHANGED: { label: 'Cambio de rol', tone: 'pill pill-info' },
  ACCESS_DEACTIVATED: { label: 'Acceso desactivado', tone: 'pill' },
  ACCESS_REACTIVATED: { label: 'Acceso reactivado', tone: 'pill pill-info' },
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
    <main className="mx-auto max-w-5xl space-y-6 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold">Actividad</h1>
        <p className="text-muted-foreground">
          Quién entró, a quién se le negó el paso, y qué cambió en los accesos.
        </p>
      </div>

      {log.items.length === 0 ? (
        <p className="text-muted-foreground">Todavía no hay nada registrado.</p>
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
                tone: 'pill',
              }
              return (
                <tr key={event.id} className="border-b last:border-0 align-top">
                  <td className="py-3 whitespace-nowrap">{shortMoment(event.occurred_at)}</td>
                  <td>
                    <span className={label.tone}>{label.label}</span>
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
    </main>
  )
}
