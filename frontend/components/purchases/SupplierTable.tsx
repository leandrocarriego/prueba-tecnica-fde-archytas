import Link from 'next/link'

import { Money } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Empty } from '@/components/ui/state'
import { count } from '@/lib/format'
import type { Supplier } from '@/lib/purchases/types'

/** Cómo se llama en pantalla cada dato que el portal no publicó. */
const MISSING_LABELS: Record<string, string> = {
  tax_id: 'CUIT',
  email: 'mail',
  phone: 'teléfono',
  payment_term_days: 'plazo',
}

/**
 * La salud del dato de un proveedor, dicha en una píldora.
 *
 * Es la columna que conecta el padrón con la bandeja de pendientes: se entra al
 * problema desde donde se lo ve. Tres estados y un orden entre ellos — falta
 * algo, hay nombres unificados, o está OK — porque la fila tiene lugar para una
 * sola señal y la que gana es la que pide trabajo.
 */
function HealthBadge({ supplier }: { supplier: Supplier }) {
  const missing = supplier.missing ?? []
  if (missing.length > 0) {
    return (
      <Badge tone="warn">
        Falta {missing.map(field => MISSING_LABELS[field] ?? field).join(', ')}
      </Badge>
    )
  }
  // Dos o más grafías son un nombre que llegó escrito de varias maneras y que
  // alguien —o una regla— unificó. Se muestra como evidencia y no se esconde:
  // quien mira tiene que poder ver de dónde sale el dato consolidado.
  const aliases = supplier.aliases ?? []
  if (aliases.length > 1) {
    return <Badge tone="info">{count(aliases.length)} nombres unificados</Badge>
  }
  return <Badge>OK</Badge>
}

/**
 * El índice de proveedores con la forma de la guía visual (`3n`).
 *
 * Cuatro columnas: quién es, cuánto se le debe, cuántas facturas tiene y la
 * salud de su dato. Ordenado por deuda, que es «lo que importa» de la guía: el
 * padrón se abre para saber quién está esperando plata.
 *
 * **La quinta columna del diseño, la puntualidad, no está.** Pedía los días
 * promedio de pago de cada proveedor y la API no los publica; dibujarla con un
 * número aproximado sería inventar la única columna que nadie podría verificar.
 * Cuando el backend la exponga, entra acá y la fila ya tiene su lugar.
 *
 * La fila con algo que resolver se marca con el borde de acento a la izquierda,
 * como en la guía: es la misma señal que usa la cola de pendientes para el caso
 * abierto, y quiere decir lo mismo — **acá hay trabajo de una persona**.
 */
export function SupplierTable({ items }: { items: Supplier[] }) {
  if (items.length === 0) {
    return (
      <Empty title="No hay proveedores que coincidan.">
        Probá con otra búsqueda, o mirá el padrón completo.
      </Empty>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <colgroup>
          <col className="w-[38%]" />
          <col className="w-[18%]" />
          <col className="w-[16%]" />
          <col className="w-[28%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-border bg-muted">
            <th className="section-label px-4 py-2.5 text-left">Proveedor</th>
            <th className="section-label px-4 py-2.5 text-right">Le debo</th>
            <th className="section-label px-4 py-2.5 text-right">Facturas</th>
            <th className="section-label px-4 py-2.5 text-left">Salud del dato</th>
          </tr>
        </thead>
        <tbody>
          {items.map(supplier => {
            const needsWork = (supplier.missing ?? []).length > 0
            return (
              <tr
                key={supplier.id}
                className={`border-b border-border align-middle ${
                  needsWork ? 'border-l-[3px] border-l-brand bg-warn-surface/40' : ''
                }`}
              >
                <td className="px-4 py-3">
                  <Link
                    className="text-sm font-medium text-foreground hover:text-link hover:underline"
                    href={`/proveedores/${supplier.id}`}
                  >
                    {supplier.legal_name}
                  </Link>
                  {/*
                    El renglón de abajo dice quién es en los términos con los que
                    se lo busca: el CUIT y el plazo acordado. Lo que falta se
                    dice **falta**, no se deja en blanco (RF-15, RF-20): una
                    celda vacía se lee igual que un dato que nadie leyó.
                  */}
                  <p className="amount mt-0.5 text-xs text-muted-ink">
                    {supplier.tax_id ?? <span className="text-warn">Sin CUIT cargado</span>}
                    {supplier.payment_term_days !== null &&
                      ` · plazo ${supplier.payment_term_days} d`}
                  </p>
                </td>
                <td className="px-4 py-3 text-right">
                  {supplier.balance === null || Number(supplier.balance) === 0 ? (
                    <span className="amount text-sm text-muted-ink">$ 0</span>
                  ) : (
                    <Money value={supplier.balance} as="span" className="text-sm font-medium" />
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="text-sm text-muted-foreground">
                    {supplier.invoice_count === 0 ? 'Ninguna' : count(supplier.invoice_count)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <HealthBadge supplier={supplier} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
