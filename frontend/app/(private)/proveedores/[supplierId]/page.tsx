import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { InvoiceTable } from '@/components/purchases/InvoiceTable'
import { SupplierContact } from '@/components/purchases/SupplierContact'
import { SupplierPeriod } from '@/components/purchases/SupplierPeriod'
import { notFound } from 'next/navigation'

import { readFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import { count, decimal, money } from '@/lib/format'
import type { CorrectionReason } from '@/lib/operations/types'
import type { InvoiceList, Supplier, SupplierTotals } from '@/lib/purchases/types'

export const metadata = {
  title: 'Proveedor — Plataforma Cordillera',
}

const MISSING_LABELS: Record<string, string> = {
  tax_id: 'CUIT',
  email: 'correo',
  phone: 'teléfono',
  payment_term_days: 'plazo de pago',
}

/**
 * Un proveedor: su ficha, sus facturas y cuánto se le debe (H3 y H5 de 004).
 *
 * La ficha muestra los cinco datos que pide RF-15 y distingue los que alguien
 * corrigió a mano. Cuando el padrón vuelve a leerse y trae otra cosa sobre un
 * dato corregido, la corrección es la que se ve y la diferencia se señala al
 * lado (RF-19): el portal no pisa lo que una persona decidió.
 *
 * Debajo de cada total va **cuántas facturas quedaron afuera** — las que están
 * en revisión y las señaladas como inconsistentes— porque un total que descarta
 * filas en silencio es un total que el cliente va a desmentir la primera vez
 * que lo verifique a mano (RF-23 de 004, RF-28 de 005).
 */
export default async function SupplierPage({
  params,
  searchParams,
}: {
  params: Promise<{ supplierId: string }>
  searchParams: Promise<{ since?: string; until?: string }>
}) {
  const { supplierId } = await params
  // El período viaja en la URL y no en el estado de un componente: «cuánto le
  // compré este año» es una pregunta que se comparte por chat, y así llega
  // contestada (RF-22).
  const { since, until } = await searchParams
  const period = new URLSearchParams()
  if (since) period.set('since', since)
  if (until) period.set('until', until)
  const query = period.toString()

  const [read, totalsRead, invoices, session] = await Promise.all([
    readFromApi<Supplier>(`/suppliers/${supplierId}`),
    readFromApi<SupplierTotals>(`/suppliers/${supplierId}/totals${query ? `?${query}` : ''}`),
    readFromApi<InvoiceList>(`/suppliers/${supplierId}/invoices?limit=200`),
    getSession(),
  ])

  if (!read.ok) {
    if (read.failure === 'unauthorized') {
      return <NoPermission what="el padrón de proveedores" />
    }
    if (read.failure === 'missing') notFound()
    return (
      <main className="mx-auto max-w-5xl space-y-6 p-8">
        <Link className="text-sm text-muted-foreground underline" href="/proveedores">
          « Volver al padrón
        </Link>
        <p className="rounded border border-danger-border bg-danger-surface p-4 text-sm text-danger">
          No pudimos traer este proveedor. Probá de nuevo en unos minutos.
        </p>
      </main>
    )
  }

  const supplier = read.data
  const totals = totalsRead.ok ? totalsRead.data : null

  // Corregir el contacto de un proveedor es `SUPPLIERS` en escritura, que el
  // dueño y compras tienen y ventas no. El backend rechaza igual a cualquier
  // otro; esto sólo evita ofrecer un botón que contesta 403.
  const mayCorrect = session !== null && canEdit(session.permissions, 'SUPPLIERS')
  const reasons = mayCorrect
    ? await readFromApi<CorrectionReason[]>('/operations/corrections/reasons')
    : null

  return (
    <main className="mx-auto max-w-5xl space-y-8 p-8">
      <Link className="text-sm text-muted-foreground underline" href="/proveedores">
        « Volver al padrón
      </Link>

      <header className="space-y-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold">{supplier.legal_name}</h1>
          <p className="text-sm text-muted-foreground">{supplier.tax_id ?? 'CUIT: falta'}</p>
        </div>
        <SupplierContact
          supplier={supplier}
          canCorrect={mayCorrect}
          reasons={reasons !== null && reasons.ok ? reasons.data : []}
        />
        {(supplier.missing ?? []).length > 0 && (
          <p className="text-sm text-warn">
            El portal no publicó:{' '}
            {(supplier.missing ?? []).map(field => MISSING_LABELS[field] ?? field).join(', ')}.
          </p>
        )}

        {/*
          Todas las formas en que llegó escrito su nombre (RF-10). El criterio
          firmado dice «al abrir un proveedor se ven todas las formas», y viajaban
          en la respuesta sin que ninguna pantalla las mostrara: estaban sólo en
          /proveedores/grafias, que es otra pregunta —qué decisiones hay
          guardadas— y no ésta —con cuántos nombres me llega este proveedor—.
        */}
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">
            Llega escrito de {count((supplier.aliases ?? []).length)}{' '}
            {(supplier.aliases ?? []).length === 1 ? 'forma' : 'formas'}:
          </p>
          <ul className="flex flex-wrap gap-2">
            {(supplier.aliases ?? []).map(alias => (
              <li
                key={alias.id}
                className="rounded bg-secondary px-2 py-0.5 font-mono text-xs"
                title={
                  alias.source === 'OBSERVED'
                    ? 'Reconocida por el sistema'
                    : 'Asignada por una persona'
                }
              >
                {alias.text_original}
              </li>
            ))}
          </ul>
          <Link className="text-sm underline" href="/proveedores/grafias">
            Ver las grafías guardadas
          </Link>
        </div>
      </header>

      {totals && (
        <section className="space-y-4">
          <SupplierPeriod supplierId={supplier.id} since={since} until={until} />

          <dl className="grid gap-4 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-muted-foreground">Facturado</dt>
              <dd className="text-lg font-medium">{money(totals.invoiced)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Pagado</dt>
              <dd className="text-lg font-medium">{money(totals.paid)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Se le debe</dt>
              <dd className="text-lg font-medium">{money(totals.owed)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Atraso promedio</dt>
              <dd className="text-lg font-medium">
                {totals.average_delay_days === null
                  ? 'sin atrasos'
                  : `${decimal(totals.average_delay_days)} días`}
              </dd>
            </div>
          </dl>

          {/*
            Qué quedó afuera, **por qué motivo**. RF-23 pregunta una cosa en
            particular —cuántas quedaron afuera por estar en revisión— y sumarle
            las que caen fuera del período elegido hacía que ese número dejara de
            contestarla en cuanto alguien elegía un período.
          */}
          <p className="text-sm text-muted-foreground">
            {count(totals.invoices)} facturas entran en estos números.{' '}
            {totals.excluded === 0
              ? 'No quedó ninguna afuera.'
              : [
                  totals.excluded_in_review > 0 && `${totals.excluded_in_review} en revisión`,
                  totals.excluded_inconsistent > 0 &&
                    `${totals.excluded_inconsistent} con pagos que superan su total`,
                  totals.excluded_out_of_period > 0 &&
                    `${totals.excluded_out_of_period} fuera del período`,
                ]
                  .filter(Boolean)
                  .join(', ') + ' quedaron afuera.'}
          </p>

          <div>
            <h2 className="mb-2 text-lg font-medium">Deuda por antigüedad</h2>
            <table className="w-full max-w-xl text-sm">
              <tbody>
                {totals.aging.map(bucket => (
                  <tr key={bucket.label} className="border-b">
                    <td className="py-2">{bucket.label}</td>
                    <td className="py-2 text-right">{money(bucket.amount)}</td>
                    <td className="py-2 text-right text-muted-foreground">
                      {count(bucket.invoices)} facturas
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Sus facturas</h2>
        <InvoiceTable invoices={invoices.ok ? invoices.data.items : []} />
      </section>
    </main>
  )
}
