'use client'

import { useState, useTransition } from 'react'

import {
  changeRole,
  deactivateAccess,
  reactivateAccess,
  type ActionResult,
  type UserRead,
} from '@/app/actions/access'

const ROLES: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'OWNER', label: 'Dueño' },
  { value: 'PURCHASING', label: 'Compras' },
  { value: 'SALES', label: 'Ventas' },
]

/** The four states of an access, derived on the backend and only shown here. */
function estado(user: UserRead): { label: string; tone: string } {
  if (!user.is_active) return { label: 'Desactivado', tone: 'bg-gray-100 text-gray-700' }
  if (!user.activated_at) return { label: 'Invitado', tone: 'bg-amber-100 text-amber-800' }
  if (user.locked_until) return { label: 'Bloqueado', tone: 'bg-red-100 text-red-800' }
  return { label: 'Activo', tone: 'bg-green-100 text-green-800' }
}

export function AccessTable({ accesos, yo }: { accesos: UserRead[]; yo: number }) {
  const [pending, startTransition] = useTransition()
  const [result, setResult] = useState<ActionResult | null>(null)

  const run = (action: () => Promise<ActionResult>) => {
    startTransition(async () => setResult(await action()))
  }

  return (
    <div className="space-y-4">
      {result && (
        <p
          className={`rounded border px-4 py-2 text-sm ${
            result.ok ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
          }`}
        >
          {result.message}
        </p>
      )}

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
          {accesos.map(acceso => {
            const { label, tone } = estado(acceso)
            const esYo = acceso.id === yo
            return (
              <tr key={acceso.id} className="border-b last:border-0">
                <td className="py-3">
                  {acceso.name}
                  {acceso.last_name ? ` ${acceso.last_name}` : ''}
                </td>
                <td className="text-muted-foreground">{acceso.email}</td>
                <td className="text-muted-foreground">{acceso.phone}</td>
                <td>
                  <select
                    defaultValue={acceso.role}
                    disabled={pending || esYo}
                    onChange={event => run(() => changeRole(acceso.id, event.target.value))}
                    className="rounded border px-2 py-1 disabled:opacity-50"
                  >
                    {ROLES.map(role => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <span className={`rounded px-2 py-1 text-xs ${tone}`}>{label}</span>
                </td>
                <td className="py-3 text-right">
                  {esYo ? (
                    // RF-22: the owner cannot lock themselves out, so the
                    // screen does not offer it. The backend refuses it anyway.
                    <span className="text-xs text-muted-foreground">Sos vos</span>
                  ) : acceso.is_active ? (
                    <button
                      type="button"
                      disabled={pending}
                      onClick={() => run(() => deactivateAccess(acceso.id))}
                      className="cursor-pointer rounded border px-3 py-1 hover:bg-gray-50 disabled:opacity-50"
                    >
                      Desactivar
                    </button>
                  ) : (
                    <button
                      type="button"
                      disabled={pending}
                      onClick={() => run(() => reactivateAccess(acceso.id))}
                      className="cursor-pointer rounded border px-3 py-1 hover:bg-gray-50 disabled:opacity-50"
                    >
                      Reactivar
                    </button>
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
