import { getSession } from '@/app/actions/auth'
import { listAccesses } from '@/app/actions/access'
import { AccessPanel } from '@/components/access/AccessPanel'
import { NoPermission } from '@/components/common/NoPermission'
import { canEdit } from '@/lib/auth/permissions'

export const metadata = {
  title: 'Accesos — Plataforma Cordillera',
}

/**
 * Administering the accesses. The owner's, and only the owner's (RF-24).
 *
 * Es la segunda pestaña de «Configuración». Vivía en `/accesos`, que ahora
 * redirige acá: dar de alta a alguien es de la misma clase de decisión que
 * mover un parámetro o elegir a quién le llega un aviso, y las tres estaban
 * repartidas en entradas distintas del menú.
 */
export default async function AccessesPage() {
  const session = await getSession()
  if (!session || !canEdit(session.permissions, 'ACCESS_ADMIN')) {
    return <NoPermission what="la administración de accesos" />
  }

  const accesses = await listAccesses()
  if (!accesses) {
    return <NoPermission what="la administración de accesos" />
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold">Accesos</h2>
        <p className="text-sm text-muted-foreground">
          Quién entra al sistema, con qué rol, y en qué estado está cada acceso.
        </p>
      </header>

      <AccessPanel accesses={accesses.items} viewerId={session.user.id} />
    </div>
  )
}
