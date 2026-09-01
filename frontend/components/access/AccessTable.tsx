'use client'

import { useState, useTransition } from 'react'

import {
  changeRole,
  deactivateAccess,
  reactivateAccess,
  type ActionResult,
  type UserRead,
} from '@/app/actions/access'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { selectClassName } from '@/components/ui/input'
import { Notice } from '@/components/ui/notice'
import type { BadgeTone } from '@/lib/ui/tone'

const ROLES: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'OWNER', label: 'Dueño' },
  { value: 'PURCHASING', label: 'Compras' },
  { value: 'SALES', label: 'Ventas' },
]

/**
 * The four states of an access, derived on the backend and only shown here.
 *
 * El tono es el de `Badge` y ya no la clase escrita a mano: éste era uno de los
 * dos archivos que dibujaban `.pill` por su cuenta, que es cómo un estado
 * termina viéndose distinto en dos pantallas (`UI-03`).
 */
function stateOf(user: UserRead): { label: string; tone: BadgeTone } {
  if (!user.is_active) return { label: 'Desactivado', tone: 'neutral' }
  if (!user.activated_at) return { label: 'Invitado', tone: 'warn' }
  if (user.locked_until) return { label: 'Bloqueado', tone: 'danger' }
  return { label: 'Activo', tone: 'ok' }
}

export function AccessTable({ accesses, viewerId }: { accesses: UserRead[]; viewerId: number }) {
  const [pending, startTransition] = useTransition()
  const [result, setResult] = useState<ActionResult | null>(null)

  const run = (action: () => Promise<ActionResult>) => {
    startTransition(async () => setResult(await action()))
  }

  return (
    <div className="space-y-4">
      {result && <Notice tone={result.ok ? 'ok' : 'danger'} title={result.message} />}

      <table className="w-full text-left text-sm">
        <thead className="border-b text-muted-foreground">
          <tr>
            <th className="py-2">Persona</th>
            <th>Correo</th>
            <th>Teléfono</th>
            <th>Rol</th>
            <th>Estado</th>
            <th className="text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {accesses.map(access => {
            const { label, tone } = stateOf(access)
            const isViewer = access.id === viewerId
            return (
              <tr key={access.id} className="border-b last:border-0">
                <td className="py-3">
                  {access.name}
                  {access.last_name ? ` ${access.last_name}` : ''}
                </td>
                <td className="text-muted-foreground">{access.email}</td>
                <td className="text-muted-foreground">{access.phone}</td>
                <td>
                  <select
                    defaultValue={access.role}
                    disabled={pending || isViewer}
                    onChange={event => run(() => changeRole(access.id, event.target.value))}
                    className={selectClassName}
                  >
                    {ROLES.map(role => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <Badge tone={tone}>{label}</Badge>
                </td>
                <td className="py-3 text-right">
                  {isViewer ? (
                    // RF-22: the owner cannot lock themselves out, so the
                    // screen does not offer it. The backend refuses it anyway.
                    <span className="text-xs text-muted-foreground">Sos vos</span>
                  ) : access.is_active ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={pending}
                      onClick={() => run(() => deactivateAccess(access.id))}
                    >
                      Desactivar
                    </Button>
                  ) : (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={pending}
                      onClick={() => run(() => reactivateAccess(access.id))}
                    >
                      Reactivar
                    </Button>
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
