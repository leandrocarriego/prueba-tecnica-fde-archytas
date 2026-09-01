import { redirect } from 'next/navigation'

/**
 * La puerta de Ventas (`RF-22`).
 *
 * El menú necesita un `href` estable para el área —`/ventas`— y hoy el área
 * tiene una sola pantalla: la revisión de lo que el sistema no pudo sumar. En
 * vez de inventar un índice que repita lo que ya está una ruta más abajo, esto
 * redirige, y el día que Ventas tenga una segunda pantalla el `href` del menú
 * no cambia.
 */
export default function SalesRoot() {
  redirect('/ventas/revision')
}
