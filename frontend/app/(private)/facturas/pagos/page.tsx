import Link from 'next/link'

import { HeldVouchers } from '@/components/purchases/HeldVouchers'
import { NoPermission } from '@/components/common/NoPermission'
import { readFromApi } from '@/lib/api/server'
import type { Invoice, InvoiceList, Payment } from '@/lib/purchases/types'

export const metadata = {
  title: 'Comprobantes por repartir — Plataforma Cordillera',
}

/**
 * Los comprobantes que esperan a que una persona diga qué cubren (H9 de 005).
 *
 * Esta pantalla es la mitad visible de una decisión del dominio: un comprobante
 * que no dice a qué factura corresponde **no se imputa por parecido** — ni por
 * monto, ni por fecha, ni por saldo que cierra— porque adivinarlo sería que la
 * plataforma decidiera adónde fue la plata de alguien. Queda apartado y espera.
 *
 * Y esperaba sin que nadie lo viera: el backend estaba entero desde el primer
 * día, `GET /payments/pending` contestaba, la Server Action de repartir estaba
 * escrita — y revalidaba **esta ruta, que no existía**. El relevamiento del
 * portal mide por qué eso importa: los comprobantes de la cuenta corriente
 * referencian su propio número de recibo y no el de la factura, así que la
 * mayoría termina acá. Sin esta pantalla, el trabajo que la plataforma le deja
 * a compras no tenía dónde hacerse.
 *
 * Las facturas candidatas se traen **por proveedor**: el reparto es entre
 * facturas de un mismo proveedor, que es el supuesto que el cliente firmó.
 */
export default async function HeldPaymentsPage() {
  const read = await readFromApi<Payment[]>('/payments/pending')

  if (!read.ok) {
    // Los tres motivos por los que no hay datos no son el mismo: mandar a una
    // persona a pedir un permiso que ya tiene, porque la API no contestó, es
    // un consejo sobre el que nadie puede actuar.
    if (read.failure === 'unauthorized') {
      return <NoPermission what="los pagos" />
    }
    return (
      <main className="mx-auto max-w-4xl space-y-4 p-8">
        <h1 className="text-2xl font-bold">Comprobantes por repartir</h1>
        <p className="rounded border border-danger-border bg-danger-surface p-4 text-sm text-danger">
          No pudimos traer los comprobantes. Probá de nuevo en unos minutos.
        </p>
      </main>
    )
  }

  const held = read.data
  // Un pedido por proveedor y no uno por comprobante: dos comprobantes del
  // mismo proveedor eligen entre las mismas facturas.
  const supplierIds = [
    ...new Set(held.map(payment => payment.supplier_id).filter(id => id !== null)),
  ]
  const invoicesBySupplier = new Map<number, Invoice[]>()
  await Promise.all(
    supplierIds.map(async supplierId => {
      const invoices = await readFromApi<InvoiceList>(`/suppliers/${supplierId}/invoices?limit=200`)
      if (invoices.ok) invoicesBySupplier.set(supplierId, invoices.data.items)
    })
  )

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <Link className="text-sm text-muted-foreground underline" href="/facturas">
        « Volver a las facturas
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Comprobantes por repartir</h1>
        <p className="text-sm text-muted-foreground">
          {held.length === 0
            ? 'No hay ningún comprobante esperando.'
            : `${held.length} ${held.length === 1 ? 'comprobante espera' : 'comprobantes esperan'} a que digas qué cubren.`}
        </p>
        <p className="text-sm text-muted-foreground">
          Hasta que un reparto esté confirmado, ningún saldo se mueve. Las partes tienen que sumar
          exactamente el monto del comprobante.
        </p>
      </header>

      {held.length === 0 ? (
        <p className="rounded border border-dashed p-8 text-center text-muted-foreground">
          Nada apartado. Cuando llegue un comprobante que no diga a qué factura corresponde, va a
          aparecer acá con el motivo, en lugar de aplicarse a la que más se le parezca.
        </p>
      ) : (
        <HeldVouchers held={held} invoicesBySupplier={Object.fromEntries(invoicesBySupplier)} />
      )}
    </main>
  )
}
