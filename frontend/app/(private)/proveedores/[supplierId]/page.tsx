import Link from 'next/link'
import { notFound } from 'next/navigation'

import { getSession } from '@/app/actions/auth'
import { Tile } from '@/components/common/Tile'
import { NoPermission } from '@/components/common/NoPermission'
import { BalanceStrip } from '@/components/purchases/BalanceStrip'
import { InvoiceTable } from '@/components/purchases/InvoiceTable'
import { SupplierContact } from '@/components/purchases/SupplierContact'
import { SupplierPeriod } from '@/components/purchases/SupplierPeriod'
import { Decimal, Money } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { ErrorState } from '@/components/ui/state'
import { readFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import { count } from '@/lib/format'
import type { CorrectionReason } from '@/lib/operations/types'
import type { InvoiceList, Supplier, SupplierTotals } from '@/lib/purchases/types'
import { isUnconfirmedSupplierAlias, pill } from '@/lib/ui/tone'

export const metadata = {
  title: 'Proveedor — Plataforma Cordillera',
}

/**
 * El renglón de identificación de la guía (`3c`): CUIT, correo y plazo, en mono,
 * debajo del nombre.
 *
 * Lo que el portal no publicó se dice **falta** y en ámbar, no se omite del
 * renglón: una identificación a la que le sacaron un dato se lee como una
 * identificación completa de un proveedor distinto (RF-15, RF-20).
 */
function Identity({ supplier }: { supplier: Supplier }) {
  const missing = <span className="text-warn">falta</span>
  return (
    <p className="amount text-[13px] text-muted-ink">
      CUIT {supplier.tax_id ?? missing}
      {' · '}
      {supplier.email ?? missing}
      {' · '}
      plazo {supplier.payment_term_days === null ? missing : `${supplier.payment_term_days} días`}
    </p>
  )
}

/**
 * Un proveedor: su ficha, su cuenta corriente y cuánto se le debe (H3 y H5 de
 * 004), con la forma de la guía visual (`3c`).
 *
 * Encabezado con el nombre y su identificación, **los nombres unificados a la
 * vista como evidencia** —el criterio firmado dice que no se esconden: quien
 * mira tiene que ver de dónde sale el dato consolidado (RF-10)—, las cuatro
 * cuentas del período y la cuenta corriente encabezada por el estado del saldo.
 *
 * **Las cinco pestañas del diseño no están, y falta decir por qué.** La guía
 * dibuja Cuenta corriente · Facturas · Pagos · Órdenes · Reclamos, y de las
 * cinco la API publica una sola por proveedor: `/suppliers/{id}/invoices`. No
 * hay pagos, órdenes ni reclamos por proveedor. Dibujar cinco solapas de las
 * cuales cuatro no tienen nada detrás sería prometer cuatro pantallas que no
 * existen; cuando el backend las publique, la barra entra acá y el contenido de
 * la primera ya está armado.
 *
 * Los totales muestran debajo **cuántas facturas quedaron afuera** —las que
 * están en revisión y las señaladas como inconsistentes— porque un total que
 * descarta filas en silencio es un total que el cliente va a desmentir la
 * primera vez que lo verifique a mano (RF-23 de 004, RF-28 de 005).
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
      <div className="space-y-4">
        <Link className="text-sm text-link hover:underline" href="/proveedores">
          « Volver al padrón
        </Link>
        <ErrorState title="No pudimos traer este proveedor." />
      </div>
    )
  }

  const supplier = read.data
  const totals = totalsRead.ok ? totalsRead.data : null
  const aliases = supplier.aliases ?? []
  const rows = invoices.ok ? invoices.data.items : []

  // Corregir el contacto de un proveedor es `SUPPLIERS` en escritura, que el
  // dueño y compras tienen y ventas no. El backend rechaza igual a cualquier
  // otro; esto sólo evita ofrecer un botón que contesta 403.
  const mayCorrect = session !== null && canEdit(session.permissions, 'SUPPLIERS')
  const reasons = mayCorrect
    ? await readFromApi<CorrectionReason[]>('/operations/corrections/reasons')
    : null

  // Los días que se tarda en pagarle, que es el plazo acordado más lo que se
  // demora sobre él. Es la cuenta que la guía pone en la cuarta tarjeta, y sólo
  // se puede hacer cuando existen las dos mitades: sin plazo pactado no hay
  // «sobre el plazo» que calcular, y la tarjeta dice eso en vez de un número.
  const delay = totals?.average_delay_days == null ? null : Number(totals.average_delay_days)
  const average =
    delay === null || supplier.payment_term_days === null
      ? null
      : supplier.payment_term_days + delay

  return (
    <div className="space-y-4">
      <header className="space-y-3 rounded-xl border border-border bg-card px-6 py-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <p className="text-xs text-muted-foreground">
              <Link className="hover:text-link hover:underline" href="/proveedores">
                Proveedores
              </Link>
              {' / '}
              <span className="text-foreground">{supplier.legal_name}</span>
            </p>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              {supplier.legal_name}
            </h1>
            <Identity supplier={supplier} />
          </div>

          <SupplierPeriod supplierId={supplier.id} since={since} until={until} />
        </div>

        {/*
          Todas las formas en que llegó escrito su nombre (RF-10), **como
          evidencia y no escondidas**: el criterio firmado dice que al abrir un
          proveedor se ven todas, porque es lo que explica de dónde sale el dato
          consolidado. La cuenta va primero, como en la guía: es el titular, y
          las grafías son la prueba.
        */}
        {aliases.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {aliases.length > 1 && (
              <Badge tone="info">{count(aliases.length)} nombres unificados</Badge>
            )}
            {aliases.map(alias => (
              /*
               * `RF-08`: la que reconoció el sistema va punteada, la que asignó
               * una persona no. La diferencia se ve sin leer el título.
               */
              <Badge
                key={alias.id}
                tone={pill('neutral', isUnconfirmedSupplierAlias(alias.source))}
                title={
                  alias.source === 'OBSERVED'
                    ? 'Reconocida por el sistema'
                    : 'Asignada por una persona'
                }
              >
                «{alias.text_original}»
              </Badge>
            ))}
            <Link className="text-xs text-link hover:underline" href="/proveedores/grafias">
              Ver las grafías guardadas
            </Link>
          </div>
        )}
      </header>

      {totals && (
        <div className="flex flex-wrap gap-4">
          <Tile
            label="Le compré"
            value={<Money value={totals.invoiced} as="span" />}
            sub={`${count(totals.invoices)} ${totals.invoices === 1 ? 'factura' : 'facturas'} en el período.`}
          />
          <Tile
            label="Le pagué"
            value={<Money value={totals.paid} as="span" />}
            sub="Pagos imputados a esas facturas."
          />
          {/*
            La única con acento: lo que se debe es lo que puede requerir una
            decisión hoy, y en cero no se pinta — un ámbar sobre un saldo saldado
            enseña que el color no quiere decir nada.
          */}
          <Tile
            label="Le debo"
            value={<Money value={totals.owed} as="span" />}
            accent={Number(totals.owed) > 0}
            sub={
              Number(totals.owed) > 0 ? 'Saldo abierto con este proveedor.' : 'Sin saldo abierto.'
            }
          />
          <Tile
            label="Pago promedio"
            value={average === null ? '—' : `${average} días`}
            sub={
              delay === null ? (
                'Todavía no hay pagos con los que calcularlo.'
              ) : delay > 0 ? (
                <span className="text-warn">
                  <Decimal value={delay} /> días más que el plazo.
                </span>
              ) : (
                'Dentro del plazo acordado.'
              )
            }
          />
        </div>
      )}

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <h2 className="text-sm font-semibold text-foreground">Cuenta corriente</h2>
        </div>
        {totals && <BalanceStrip invoices={rows} total={totals.invoiced} />}
        <div className="px-4 py-2">
          <InvoiceTable invoices={rows} />
        </div>
      </section>

      {totals && (
        <>
          {/*
            Qué quedó afuera, **por qué motivo**. RF-23 pregunta una cosa en
            particular —cuántas quedaron afuera por estar en revisión— y sumarle
            las que caen fuera del período elegido hacía que ese número dejara de
            contestarla en cuanto alguien elegía un período.
          */}
          <p className="text-xs text-muted-foreground">
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

          <section className="space-y-3 rounded-xl border border-border bg-card p-6">
            <h2 className="text-sm font-semibold text-foreground">Deuda por antigüedad</h2>
            <table className="w-full max-w-xl text-sm">
              <tbody>
                {totals.aging.map(bucket => (
                  <tr key={bucket.label} className="border-b border-border last:border-0">
                    <td className="py-2">{bucket.label}</td>
                    <Money value={bucket.amount} cell className="py-2" />
                    <td className="amount py-2 text-right text-muted-foreground">
                      {count(bucket.invoices)} facturas
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}

      {/*
        Los datos de contacto y su corrección (RF-16, RF-19). Van al pie y no en
        el encabezado porque son lo que se abre a cambiar de tanto en tanto, no
        lo que se viene a consultar: arriba está la identificación, que es la que
        se lee siempre.
      */}
      <section className="space-y-3 rounded-xl border border-border bg-card p-6">
        <h2 className="text-sm font-semibold text-foreground">Datos de contacto</h2>
        <SupplierContact
          supplier={supplier}
          canCorrect={mayCorrect}
          reasons={reasons !== null && reasons.ok ? reasons.data : []}
        />
      </section>
    </div>
  )
}
