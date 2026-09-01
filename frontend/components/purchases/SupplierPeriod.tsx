import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

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
        <Input name="since" type="date" defaultValue={since ?? ''} />
      </label>
      <label>
        <span className="mb-1 block text-muted-foreground">Hasta</span>
        <Input name="until" type="date" defaultValue={until ?? ''} />
      </label>
      {/* Acotar el período no es la tarea de la ficha: leerla lo es. */}
      <Button type="submit" variant="outline">
        Ver el período
      </Button>
      {/* Los dos atajos son navegación —cambian lo que se mira, no los datos—. */}
      <a
        className="text-link hover:underline"
        href={`/proveedores/${supplierId}?since=${year}-01-01&until=${year}-12-31`}
      >
        Año en curso
      </a>
      {(since || until) && (
        <a className="text-link hover:underline" href={`/proveedores/${supplierId}`}>
          Todo
        </a>
      )}
    </form>
  )
}
