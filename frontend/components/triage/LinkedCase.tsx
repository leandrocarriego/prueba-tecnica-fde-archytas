import Link from 'next/link'

import { CaseHeader } from '@/components/triage/CaseHeader'
import { Button } from '@/components/ui/button'
import type { Case } from '@/lib/triage/types'

/**
 * Las clases de caso que **se resuelven en su propia pantalla**, y a dónde va
 * cada una.
 *
 * Una factura apartada se resuelve eligiendo su proveedor, y un proveedor
 * incompleto cargando el dato que falta: las dos cosas tienen su formulario, con
 * su validación y su registro, en la pantalla de la entidad. Reconstruirlos acá
 * adentro sería una segunda copia de los dos, y la copia se desactualiza.
 *
 * Lo que la cola aporta no es el formulario: es **enterarse**. Estos dos venían
 * esperando en pantallas a las que hay que acordarse de entrar.
 */
const DOORS: Record<string, { to: (key: string) => string; label: string; fields: string[] }> = {
  invoice_in_review: {
    to: key => `/facturas/${key}`,
    label: 'Abrir la factura',
    fields: ['number', 'supplier', 'total'],
  },
  incomplete_supplier: {
    to: key => `/proveedores/${key}`,
    label: 'Abrir el proveedor',
    fields: ['supplier', 'missing'],
  },
}

/** Las clases que dibuja este panel. */
export const LINKED_CASE_KINDS: readonly string[] = Object.keys(DOORS)

/** Cómo se nombra en pantalla cada dato que el caso trae en su payload. */
const LABELS: Record<string, string> = {
  number: 'Número',
  supplier: 'Proveedor',
  total: 'Total',
  missing: 'Qué falta',
}

function text(item: Case, field: string): string {
  const value = item.payload[field]
  return typeof value === 'string' || typeof value === 'number' ? String(value) : '—'
}

/**
 * Un pendiente que se ve acá y se resuelve allá.
 *
 * Misma caja y misma cabeza que los otros paneles de la cola —quien la recorre
 * tiene que ver lo mismo arriba en todos—, y en lugar de controles, lo que el
 * caso sabe y la puerta.
 *
 * **No ofrece «darlo por revisado»**, y es deliberado: cerrar el caso sin
 * resolver la factura sería sacar de la lista algo que sigue pendiente, que es
 * la única cosa que esta cola no puede hacer (Artículo II). Se cierra solo
 * cuando el módulo dueño deja de informarlo, así que la vuelta atrás no hace
 * falta pedirla.
 */
export function LinkedCase({ item }: { item: Case }) {
  const door = DOORS[item.kind]
  const key = typeof item.payload.key === 'string' ? item.payload.key : null

  return (
    <div className="flex h-full flex-col gap-5 rounded-xl border border-border bg-card p-6">
      <CaseHeader item={item} />

      {door && (
        <>
          <dl className="grid gap-4 rounded-lg border border-border bg-muted p-4 sm:grid-cols-2">
            {door.fields.map(field => (
              <div key={field} className="min-w-0">
                <dt className="section-label">{LABELS[field] ?? field}</dt>
                <dd className="mt-1.5 text-sm text-foreground">{text(item, field)}</dd>
              </div>
            ))}
          </dl>

          <div className="flex flex-wrap items-center gap-3">
            {/*
              Sin la llave no hay a dónde ir. Pasa con un caso abierto por una
              versión anterior, que no la guardaba: se dice, en vez de dibujar un
              botón que lleva a `/facturas/undefined`.
            */}
            {key === null ? (
              <p className="text-sm text-muted-foreground">
                Este caso no guarda a qué registro apunta. Va a volver a abrirse completo en la
                próxima puesta al día.
              </p>
            ) : (
              <Button asChild variant="outline">
                <Link href={door.to(key)}>{door.label}</Link>
              </Button>
            )}
            <p className="text-xs text-muted-foreground">
              Se resuelve ahí y el caso se va solo de esta lista.
            </p>
          </div>
        </>
      )}
    </div>
  )
}
