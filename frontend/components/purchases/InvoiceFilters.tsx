import type { Supplier } from '@/lib/purchases/types'

/** Cómo se puede ordenar la lista, en las palabras que se leen (RF-45 de 004). */
const ORDERS: { value: string; label: string }[] = [
  { value: 'issued_desc', label: 'Fecha, de la más nueva' },
  { value: 'issued_asc', label: 'Fecha, de la más vieja' },
  { value: 'total_desc', label: 'Monto, de mayor a menor' },
  { value: 'total_asc', label: 'Monto, de menor a mayor' },
]

export interface InvoiceFilterValues {
  q?: string
  supplier_id?: string
  issued_from?: string
  issued_to?: string
  order?: string
}

/**
 * Buscar y ordenar las facturas (H8 de 004).
 *
 * Un `<form>` con `action="/facturas"` y nada de estado propio: los filtros
 * viajan en la URL, así que una pantalla ya filtrada se comparte por chat y
 * llega filtrada. Es la misma decisión que ya tomaba la pantalla para su
 * búsqueda; acá se completa con lo que faltaba.
 *
 * Los filtros que la barra de arriba resuelve con un link —estado de pago,
 * estado de revisión, sin recibo— no se repiten acá: dos controles para la
 * misma pregunta terminan contradiciéndose.
 */
export function InvoiceFilters({
  suppliers,
  values,
}: {
  suppliers: Supplier[]
  values: InvoiceFilterValues
}) {
  return (
    <form className="flex flex-wrap items-end gap-3" action="/facturas">
      <label className="text-sm">
        <span className="mb-1 block text-muted-foreground">Número, CUIT o proveedor</span>
        <input
          className="rounded border px-3 py-1.5"
          name="q"
          defaultValue={values.q ?? ''}
          maxLength={255}
        />
      </label>

      <label className="text-sm">
        <span className="mb-1 block text-muted-foreground">Proveedor</span>
        <select
          className="rounded border px-3 py-1.5"
          name="supplier_id"
          defaultValue={values.supplier_id ?? ''}
        >
          <option value="">Todos</option>
          {suppliers.map(supplier => (
            <option key={supplier.id} value={String(supplier.id)}>
              {supplier.legal_name}
            </option>
          ))}
        </select>
      </label>

      <label className="text-sm">
        <span className="mb-1 block text-muted-foreground">Emitidas desde</span>
        <input
          className="rounded border px-3 py-1.5"
          name="issued_from"
          type="date"
          defaultValue={values.issued_from ?? ''}
        />
      </label>

      <label className="text-sm">
        <span className="mb-1 block text-muted-foreground">Hasta</span>
        <input
          className="rounded border px-3 py-1.5"
          name="issued_to"
          type="date"
          defaultValue={values.issued_to ?? ''}
        />
      </label>

      <label className="text-sm">
        <span className="mb-1 block text-muted-foreground">Ordenar por</span>
        <select
          className="rounded border px-3 py-1.5"
          name="order"
          defaultValue={values.order ?? 'issued_desc'}
        >
          {ORDERS.map(order => (
            <option key={order.value} value={order.value}>
              {order.label}
            </option>
          ))}
        </select>
      </label>

      <button className="rounded border px-3 py-1.5 text-sm hover:bg-muted" type="submit">
        Buscar
      </button>
    </form>
  )
}
