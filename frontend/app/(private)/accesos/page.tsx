import { getSession } from '@/app/actions/auth'
import { listAccesses } from '@/app/actions/access'
import { NewAccessForm } from '@/components/access/NewAccessForm'
import { AccessTable } from '@/components/access/AccessTable'
import { NoPermission } from '@/components/common/NoPermission'
import { canEdit } from '@/lib/auth/permissions'

/** Administering the accesses. The owner's, and only the owner's (RF-24). */
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
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Accesos</h1>
        <p className="text-muted-foreground">
          Quién entra al sistema, con qué rol, y en qué estado está cada acceso.
        </p>
      </div>

      <NewAccessForm />
      <AccessTable accesses={accesses.items} viewerId={session.user.id} />
    </div>
  )
}
