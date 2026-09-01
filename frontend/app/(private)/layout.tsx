import { redirect } from 'next/navigation'

import { getSession } from '@/app/actions/auth'
import { Navigation } from '@/components/auth/Navigation'
import { fetchFromApi } from '@/lib/api/server'
import type { CaseList } from '@/lib/triage/types'

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
    Cuántos esperan una decisión, para la señal roja del menú.

    Se pide acá y no en cada pantalla porque el menú está en todas: quien está
    mirando una factura tiene que enterarse de que hay algo apartado sin volver
    a «Para decidir» a fijarse. Es `limit=1` porque de la lista sólo se usa el
    total, y ese total lo recorta el backend a las áreas que esta persona
    alcanza (RF-12), así que nadie ve en el menú un número que la pantalla le
    va a esconder.

    Si la API no contesta, el menú se dibuja sin señal: un contador es una
    comodidad, y ninguna pantalla se cae porque falte.
  */
  const queue = await fetchFromApi<CaseList>('/triage/cases?limit=1')

  /*
   * La forma del shell es la de la guía visual: barra lateral fija en tinta
   * grafito y el contenido sobre papel cálido. En pantallas angostas la barra
   * se apila arriba en vez de comerse el ancho de la tabla que se vino a leer,
   * y **se pliega**: apilada entera dejaba el contenido debajo de una pantalla
   * y media de menú, que es por lo que RF-41 de la 006 no se cumplía. Quién lo
   * decide es `Navigation`; acá sólo se la ubica.
   */
  return (
    <div className="flex min-h-dvh flex-col bg-background md:flex-row">
      <Navigation
        user={session.user}
        permissions={session.permissions}
        counters={{ triage: queue?.pending_total ?? 0 }}
      />
      <div className="min-w-0 flex-1">
        {/*
         * El fondo de aplicación y el ancho de la columna los pone el shell, y
         * **ninguna pantalla pone el suyo** (`RF-01`, `RF-02`). Antes cada una
         * elegía: `max-w-2xl` en salud, `max-w-6xl` en facturas, `max-w-5xl` en
         * proveedores, y pasar de una a otra movía el contenido de lugar. Que
         * sea una sola decisión, tomada acá, es lo que hace que la plataforma
         * se sienta una sola aplicación y no dieciséis pantallas parecidas.
         *
         * Una pantalla que necesita una columna más angosta —un formulario— la
         * angosta **adentro**, sobre su tarjeta: eso es la forma de un
         * contenido, no el ancho de la aplicación.
         */}
        <main className="mx-auto w-full max-w-6xl p-6 md:p-8">{children}</main>
      </div>
    </div>
  )
}
