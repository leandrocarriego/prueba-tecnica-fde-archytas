import { NoPermission } from '@/components/common/NoPermission'
import { AlertRoutes } from '@/components/notifications/AlertRoutes'
import { ErrorState } from '@/components/ui/state'
import { readFromApi } from '@/lib/api/server'
import type { AlertRoute } from '@/lib/notifications/types'

export const metadata = {
  title: 'Notificaciones — Plataforma Cordillera',
}

/**
 * Quién recibe cada aviso que dispara el sistema (RF-37 de 007).
 *
 * Era el último bloque de la pantalla de parámetros, debajo de dieciséis
 * tarjetas, que es tanto como estar escondido: elegir a quién le suena el
 * teléfono a las siete de la mañana no es una nota al pie de los parámetros.
 * Acá es una sección propia, con su rótulo en la fila de pestañas.
 *
 * Misma sección de permisos que los parámetros —`SYSTEM_PARAMETERS`—, así que
 * quien llega a una llega a la otra, y el gate lo sigue dando el endpoint.
 */
export default async function NotificationsPage() {
  const read = await readFromApi<AlertRoute[]>('/alerts/routes')

  if (!read.ok) {
    if (read.failure === 'unauthorized') {
      return <NoPermission what="la configuración de los avisos" />
    }
    return (
      <ErrorState title="No pudimos traer la configuración de los avisos.">
        Probá de nuevo en unos minutos.
      </ErrorState>
    )
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold">Notificaciones</h2>
        <p className="text-sm text-muted-foreground">
          Cada aviso que dispara el sistema llega por WhatsApp al número registrado de quien elijas
          acá. Ventas no figura: no accede a la bandeja de mensajes de la que hablan estos avisos.
        </p>
      </header>

      <AlertRoutes routes={read.data} />
    </div>
  )
}
