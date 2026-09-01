import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { Tabs } from '@/components/ui/tabs'
import { canSee, type Section } from '@/lib/auth/permissions'

/**
 * Configuración: una sola entrada del menú, cuatro secciones adentro.
 *
 * Parámetros, actualizaciones, accesos y avisos son la misma clase de decisión
 * —cosas que el dueño define una vez y rigen para todo el equipo—, así que
 * comparten pantalla. Cada sección sigue siendo su propia ruta.
 *
 * **«Actualizaciones» es la más nueva y la que más se pidió**: todo lo que la
 * plataforma sabe lo trajo del portal, y hasta que existió, cada extracción se
 * administraba por su cuenta — cuatro frecuencias sueltas entre las tarjetas de
 * «Parámetros» y un único botón de «traerlo ahora», el de la lista de precios.
 *
 * **La pestaña que no se puede abrir no aparece**, igual que en la barra
 * lateral: esconder el rótulo es una comodidad y la negativa la sigue dando el
 * backend en cada pantalla. Hoy las cuatro son del dueño, así que quien llega a
 * una llega a las cuatro; el filtro está igual porque el día que una sección se
 * abra a otro rol, esta pantalla ya sabe qué hacer.
 */
const TABS: ReadonlyArray<{ href: string; label: string; section: Section }> = [
  { href: '/configuracion', label: 'Parámetros', section: 'SYSTEM_PARAMETERS' },
  {
    href: '/configuracion/actualizaciones',
    label: 'Actualizaciones',
    section: 'SYSTEM_PARAMETERS',
  },
  { href: '/configuracion/accesos', label: 'Accesos', section: 'ACCESS_ADMIN' },
  { href: '/configuracion/notificaciones', label: 'Notificaciones', section: 'SYSTEM_PARAMETERS' },
]

export default async function ConfigurationLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession()
  const tabs = TABS.filter(tab => session && canSee(session.permissions, tab.section))

  // Ninguna de las tres es suya: la negativa se da una vez acá, en vez de
  // dibujar una fila de pestañas que sólo llevan a tres negativas iguales.
  if (tabs.length === 0) {
    return <NoPermission what="la configuración del sistema" />
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Configuración</h1>
        <p className="text-sm text-muted-foreground">
          Lo que decidís vos y rige para todo el equipo: los valores del sistema, quién entra y a
          quién le llega cada aviso.
        </p>
      </header>

      <Tabs tabs={tabs} label="Secciones de la configuración" />

      {children}
    </div>
  )
}
