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
 * Las cuatro primeras son de la 001, la quinta de la 008, y las dos últimas de
 * la 004 y la 007: la cola es genérica a propósito y no cambió de forma para
 * tomar ninguna.
 */
export const CASE_KINDS = {
  unreadable_row: 'Fila que no se pudo interpretar',
  unknown_product: 'Producto desconocido',
  missing_product: 'Producto que dejó de figurar',
  unreadable_history: 'Historial que no se pudo leer',
  unknown_category: 'Forma escrita sin rubro',
  unreadable_invoice_row: 'Fila de facturas que no se pudo interpretar',
  unreadable_order_row: 'Fila de órdenes de compra que no se pudo interpretar',
} as const satisfies Record<string, string>

export function caseKindLabel(kind: string): string {
  return kind in CASE_KINDS ? CASE_KINDS[kind as keyof typeof CASE_KINDS] : kind
}
