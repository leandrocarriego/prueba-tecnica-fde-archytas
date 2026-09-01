import { redirect } from 'next/navigation'

/**
 * Los accesos se mudaron a `/configuracion/accesos`.
 *
 * La ruta vieja se queda redirigiendo y no se borra: está en el historial del
 * navegador del dueño, y puede estar pegada en un mensaje. Una pantalla que
 * cambia de lugar no tiene por qué convertir un enlace guardado en un 404.
 */
export default function AccessesMoved() {
  redirect('/configuracion/accesos')
}
