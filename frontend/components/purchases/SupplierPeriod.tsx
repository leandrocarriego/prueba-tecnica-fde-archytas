/**
 * El período sobre el que se pide el total de un proveedor (RF-22 de 004).
 *
 * La API aceptaba `since` y `until` desde el primer día y esta pantalla llamaba
 * a `/totals` sin ninguno de los dos, así que el total era siempre el de todo el
 * tiempo — y el criterio firmado es «se abre un proveedor, **se pide el año en
 * curso**, y el total coincide con la suma hecha a mano». Un requisito no está
 * cumplido porque el endpoint acepte el parámetro.
 *
 * Un `<form>` con `method="get"` y nada de estado propio: el período viaja en la
 * URL, así que un total ya acotado se comparte y llega acotado. Es la misma
 * decisión que toman los filtros de la pantalla de facturas.
 *
 * El atajo al año en curso está porque es la pregunta que el cliente hizo con
 * esas palabras, y escribir dos fechas para hacerla es exactamente la fricción
 * que hace que una pantalla se abandone.
 */
export function SupplierPeriod({
  supplierId,
  since,
  until,
}: {
  supplierId: number
  since?: string
  until?: string
}) {
  const year = new Date().getFullYear()

  return (
    <form className="flex flex-wrap items-end gap-3 text-sm" action={`/proveedores/${supplierId}`}>
      <label>
        <span className="mb-1 block text-muted-foreground">Desde</span>
        <input
          className="rounded border px-3 py-1.5"
          name="since"
          type="date"
          defaultValue={since ?? ''}
        />
      </label>
      <label>
        <span className="mb-1 block text-muted-foreground">Hasta</span>
        <input
          className="rounded border px-3 py-1.5"
          name="until"
          type="date"
          defaultValue={until ?? ''}
        />
      </label>
      <button className="rounded border px-3 py-1.5 hover:bg-muted" type="submit">
        Ver el período
      </button>
      <a
        className="underline text-muted-foreground"
        href={`/proveedores/${supplierId}?since=${year}-01-01&until=${year}-12-31`}
      >
        Año en curso
      </a>
      {(since || until) && (
        <a className="underline text-muted-foreground" href={`/proveedores/${supplierId}`}>
          Todo
        </a>
      )}
    </form>
  )
}
