/**
 * Review queue types, derived from the generated OpenAPI schema.
 *
 * The queue is deliberately generic on the backend — a case has a `kind` and a
 * free-form `payload` — so what is written by hand here is only how each kind
 * is *shown*, never the contract itself.
 */
import type { components } from '@/lib/api/types'

export type Case = components['schemas']['CaseRead']
export type CaseList = components['schemas']['CaseList']
export type Rule = components['schemas']['RuleRead']

/**
 * Las clases de caso que la cola muestra hoy.
 *
 * Las cuatro primeras son de la 001, la quinta de la 008, y las dos siguientes
 * de la 004 y la 007: la cola es genérica a propósito y no cambió de forma para
 * tomar ninguna.
 *
 * Las **cuatro últimas** son de la 011, y son las que terminan de cumplir la
 * promesa: hasta esa feature el sistema apartaba una fila del padrón, un
 * comprobante ilegible, un mensaje del buzón o una venta que no podía
 * interpretar, y no se lo contaba a nadie. Quedaban guardadas y contadas, que
 * para el que tiene que decidir es lo mismo que si se hubieran perdido.
 */
export const CASE_KINDS = {
  unreadable_row: 'Fila que no se pudo interpretar',
  unknown_product: 'Producto desconocido',
  missing_product: 'Producto que dejó de figurar',
  unreadable_history: 'Historial que no se pudo leer',
  unknown_category: 'Forma escrita sin rubro',
  unreadable_invoice_row: 'Fila de facturas que no se pudo interpretar',
  unreadable_order_row: 'Fila de órdenes de compra que no se pudo interpretar',
  unreadable_supplier_row: 'Fila del padrón de proveedores que no se pudo interpretar',
  unreadable_payment_row: 'Comprobante de pago que no se pudo interpretar',
  unreadable_message_row: 'Mensaje del buzón que no se pudo interpretar',
  unreadable_sale_row: 'Venta que no se pudo interpretar',
} as const satisfies Record<string, string>

/**
 * Las clases que sólo se pueden dar por revisadas.
 *
 * No es una limitación que haya que disculpar: una fila que el portal publicó
 * rota no se puede arreglar desde acá —el origen es de sólo lectura— y cargarla
 * a mano quedó fuera de alcance. Lo que una persona puede hacer es verla,
 * entenderla y dejar constancia de que la vio, que es más de lo que había.
 */
export const ACKNOWLEDGE_ONLY_KINDS: readonly string[] = [
  'unreadable_invoice_row',
  'unreadable_order_row',
  'unreadable_supplier_row',
  'unreadable_payment_row',
  'unreadable_message_row',
  'unreadable_sale_row',
]

export function caseKindLabel(kind: string): string {
  return kind in CASE_KINDS ? CASE_KINDS[kind as keyof typeof CASE_KINDS] : kind
}

/** Las áreas del negocio, como las nombra la pantalla. */
export const SECTION_LABELS = {
  PURCHASING: 'Compras',
  SALES: 'Ventas',
  SYSTEM: 'Sistema',
} as const satisfies Record<string, string>

export function sectionLabel(section: string): string {
  return section in SECTION_LABELS
    ? SECTION_LABELS[section as keyof typeof SECTION_LABELS]
    : section
}
