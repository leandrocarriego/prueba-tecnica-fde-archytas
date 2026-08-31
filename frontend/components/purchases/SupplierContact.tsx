import { SupplierCorrection } from '@/components/purchases/SupplierCorrection'
import type { CorrectionReason } from '@/lib/operations/types'
import { isConflicted, markFor, SUPPLIER_FIELD_LABELS } from '@/lib/purchases/corrections'
import type { Supplier, SupplierCorrectionMark } from '@/lib/purchases/types'

/**
 * Los tres datos de contacto de la ficha, en el orden en que se leen.
 *
 * Son exactamente los tres que `SupplierContactWrite` admite: la razón social y
 * el CUIT no están porque no se editan (RF-17), y no hace falta decirlo dos
 * veces — el contrato no los acepta.
 */
const FIELDS: { field: 'email' | 'phone' | 'payment_term_days'; label: string }[] = [
  { field: 'email', label: 'Correo' },
  { field: 'phone', label: 'Teléfono' },
  { field: 'payment_term_days', label: 'Plazo pactado' },
]

/** Lo que muestra una celda: el valor, o «falta» cuando el portal no lo publicó. */
function shown(supplier: Supplier, field: string): string {
  const value = supplier[field as keyof Supplier]
  if (value === null || value === undefined) {
    return 'falta'
  }
  return field === 'payment_term_days' ? `${String(value)} días` : String(value)
}

/** Cómo se lee un valor del padrón dentro de una aclaración. */
function asText(value: unknown, field: string): string {
  if (value === null || value === undefined) {
    return 'no lo publicaba'
  }
  return field === 'payment_term_days' ? `${String(value)} días` : String(value)
}

/**
 * El contacto de un proveedor: correo, teléfono y plazo pactado (RF-15 de 004).
 *
 * Lo corregido a mano se distingue de lo que trajo el portal, y cuando una
 * lectura posterior del padrón trae otra cosa, **la corrección sigue en pie** y
 * la diferencia se muestra al lado como algo para mirar, nunca como el valor
 * vigente (RF-19). Es la misma lectura que hace la pantalla de precios sobre un
 * precio corregido, porque es la misma pregunta.
 *
 * Y se corrige **desde acá** (RF-16), que es donde el criterio firmado lo pide:
 * «Marcela corrige el correo de un proveedor desde su ficha». El botón sólo
 * aparece para quien la ruta dejaría escribir — ofrecerlo a quien va a recibir
 * un 403 es mentirle a la persona, no protegerla.
 */
export function SupplierContact({
  supplier,
  reasons = [],
  canCorrect = false,
}: {
  supplier: Supplier
  reasons?: CorrectionReason[]
  canCorrect?: boolean
}) {
  const corrections = (supplier.corrections ?? []) as SupplierCorrectionMark[]

  return (
    <dl className="grid gap-4 text-sm sm:grid-cols-3">
      {FIELDS.map(({ field, label }) => {
        const mark = markFor(corrections, field)
        return (
          <div key={field}>
            <dt className="text-muted-foreground">{label}</dt>
            <dd className="text-base font-medium">
              {shown(supplier, field)}
              {mark && (
                <span className="block text-xs font-normal text-muted-foreground">
                  Corregido a mano · el portal decía {asText(mark.portal_value, field)}
                </span>
              )}
              {isConflicted(mark) && (
                <span className="mt-1 block rounded bg-danger-surface px-2 py-0.5 text-xs text-danger">
                  El portal ahora informa {asText(mark?.conflict_value, field)}. Se conserva{' '}
                  {SUPPLIER_FIELD_LABELS[field] ?? 'el dato'} corregido.
                </span>
              )}
              {canCorrect && reasons.length > 0 && (
                <span className="mt-2 block">
                  <SupplierCorrection
                    supplierId={supplier.id}
                    field={field}
                    fieldLabel={label.toLowerCase()}
                    currentValue={
                      supplier[field] === null || supplier[field] === undefined
                        ? ''
                        : String(supplier[field])
                    }
                    reasons={reasons}
                  />
                </span>
              )}
            </dd>
          </div>
        )
      })}
    </dl>
  )
}
