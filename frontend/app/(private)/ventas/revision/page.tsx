import { redirect } from 'next/navigation'

/**
 * La revisión de ventas se mudó a «Para decidir».
 *
 * Era la única pantalla del área, y era una segunda cola de pendientes: lo
 * repetido y lo roto esperaban acá mientras todo lo demás que la plataforma
 * aparta esperaba en `/revision`. RF-06 de la 011 pide **una sola lista de lo
 * que está pendiente**, y dos listas no son una aunque las dos estén bien
 * hechas.
 *
 * La ruta se queda redirigiendo, con el área ya elegida: puede estar en el
 * historial de quien la usaba todos los días.
 */
export default function SalesReviewMoved() {
  redirect('/revision?area=SALES')
}
