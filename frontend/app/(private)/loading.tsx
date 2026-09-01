import { Loading } from '@/components/ui/state'

/**
 * Lo que se ve mientras cualquier pantalla del área privada espera sus datos.
 *
 * Va acá y no en cada pantalla porque Next.js lo aplica a todo el árbol de una
 * sola vez: es la forma de que `RF-19` sea cierto también en las pantallas que
 * nadie se acordó de tocar.
 */
export default function PrivateLoading() {
  return <Loading />
}
