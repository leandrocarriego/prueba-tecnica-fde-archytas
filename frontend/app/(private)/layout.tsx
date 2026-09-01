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

  /*
   * La forma del shell es la de la guía visual: barra lateral fija en tinta
   * grafito y el contenido sobre papel cálido. En pantallas angostas la barra
   * se apila arriba en vez de comerse el ancho de la tabla que se vino a leer,
   * y **se pliega**: apilada entera dejaba el contenido debajo de una pantalla
   * y media de menú, que es por lo que RF-41 de la 006 no se cumplía. Quién lo
   * decide es `Navigation`; acá sólo se la ubica.
   */
  return (
    <div className="flex min-h-dvh flex-col md:flex-row">
      <Navigation user={session.user} permissions={session.permissions} />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  )
}
