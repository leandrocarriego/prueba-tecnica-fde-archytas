import { redirect } from 'next/navigation'

/**
 * La raíz del área privada no es una pantalla: es una puerta (`RF-24`).
 *
 * Acá había una bienvenida —«Plataforma Cordillera», el mail de quien entró y
 * dos enlaces subrayados— que no es ninguna de las dieciséis secciones y que
 * nadie pidió: quedó del andamio del primer día. Lo que una persona viene a ver
 * al entrar es cómo está el negocio, y eso es el tablero.
 *
 * `redirect` y no un `page.tsx` que dibuje el tablero: la ruta `/tablero`
 * existe, está en el menú y es la que se comparte. Dos rutas que muestran lo
 * mismo terminan divergiendo.
 */
export default function PrivateRoot() {
  redirect('/tablero')
}
