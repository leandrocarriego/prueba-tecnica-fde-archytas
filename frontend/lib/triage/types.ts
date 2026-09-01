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
  /*
    Las dos que abre la carga manual. No existían mientras la única salida de
    una fila ilegible era darla por revisada: aparecen cuando una persona
    reconstruyó la factura o la orden, y el portal la publicó después ya
    legible y distinta.
  */
  disputed_invoice: 'Factura cargada a mano que el portal trajo distinta',
  disputed_order: 'Orden cargada a mano que el portal trajo distinta',
} as const satisfies Record<string, string>

/**
 * Las clases que una persona puede **cargar a mano**, y qué carga.
 *
 * Es la otra mitad del Artículo II. Hasta acá una fila que el portal publicaba
 * rota sólo se podía dar por revisada: quedaba contada y visible —que ya era
 * más de lo que había— y el dato no entraba nunca, así que la factura no
 * figuraba en ningún total ni en el calendario de vencimientos. Avisar sin
 * dejar arreglar es la mitad de una promesa.
 *
 * Siguen admitiendo «darlo por revisado», y no como consuelo: el papel puede no
 * estar a mano, y cerrar el caso sin el dato es una respuesta honesta.
 */
export const LOADABLE_KINDS = {
  unreadable_invoice_row: 'invoice',
  unreadable_order_row: 'order',
} as const satisfies Record<string, string>

/** Las dos clases en las que hay que elegir entre dos valores. */
export const DISPUTED_KINDS: readonly string[] = ['disputed_invoice', 'disputed_order']

/**
 * Las clases que **sólo** se pueden dar por revisadas.
 *
 * Eran seis y ahora son cuatro: las facturas y las órdenes se pueden cargar a
 * mano (`LOADABLE_KINDS`). Las cuatro que quedan no es que falten: un
 * comprobante, un mensaje del buzón o una fila del padrón que el portal publicó
 * rota no tienen dónde entrar de este lado, y reconstruirlos a mano sería
 * inventar un dato del que nadie tiene el papel. Lo que una persona puede hacer
 * es verlos, entenderlos y dejar constancia de que los vio.
 */
export const ACKNOWLEDGE_ONLY_KINDS: readonly string[] = [
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
