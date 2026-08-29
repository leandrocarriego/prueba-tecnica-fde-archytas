import { redirect } from 'next/navigation'

import { getSession } from '@/app/actions/auth'
import { Navigation } from '@/components/auth/Navigation'

/**
 * Layout for the protected area of the app.
 * Every page under app/(private)/* is authenticated here, on the server.
 *
 * Add a domain module by creating app/(private)/<module>/page.tsx — it is
 * protected automatically (e.g. app/(private)/suppliers/page.tsx → /suppliers).
 *
 * The session carries the permission map, so the menu below is built from what
 * the backend enforces. A session that went idle or was revoked resolves to
 * nothing here and the person lands back on the login (RF-05, RF-20).
 */
export default async function PrivateLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession()

  if (!session) {
    redirect('/login')
  }

  return (
    <>
      <Navigation user={session.user} permissions={session.permissions} />
      {children}
    </>
  )
}
