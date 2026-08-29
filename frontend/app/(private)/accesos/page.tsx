import { getSession } from '@/app/actions/auth'
import { listAccesses } from '@/app/actions/access'
import { NewAccessForm } from '@/components/access/NewAccessForm'
import { AccessTable } from '@/components/access/AccessTable'
import { NoPermission } from '@/components/common/NoPermission'
import { canEdit } from '@/lib/auth/permissions'

/** Administering the accesses. The owner's, and only the owner's (RF-24). */
export default async function AccesosPage() {
  const session = await getSession()
  if (!session || !canEdit(session.permissions, 'ACCESS_ADMIN')) {
    return <NoPermission que="la administración de accesos" />
  }

  const accesos = await listAccesses()
  if (!accesos) {
    return <NoPermission que="la administración de accesos" />
  }

  return (
    <main className="mx-auto max-w-5xl space-y-8 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold">Accesos</h1>
        <p className="text-muted-foreground">
          Quién entra al sistema, con qué rol, y en qué estado está cada acceso.
        </p>
      </div>

      <NewAccessForm />
      <AccessTable accesos={accesos.items} yo={session.user.id} />
    </main>
  )
}
