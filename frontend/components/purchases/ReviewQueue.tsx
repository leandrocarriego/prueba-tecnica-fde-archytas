'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { previewAlias, resolveInvoice } from '@/app/actions/purchases'
import type { InvoiceCorrections } from '@/app/actions/purchases'
import { Button } from '@/components/ui/button'
import { day, money } from '@/lib/format'
import type { Invoice, Supplier } from '@/lib/purchases/types'

/** Los tres datos de cabecera que una persona puede confirmar o corregir (RF-31). */
const HEADER_FIELDS: {
  field: keyof InvoiceCorrections
  label: string
  type: 'text' | 'date' | 'number'
  from: (invoice: Invoice) => string
  read: (invoice: Invoice) => string | null | undefined
}[] = [
  {
    field: 'number',
    label: 'Número',
    type: 'text',
    from: invoice => invoice.number,
    read: invoice => invoice.document?.read_number,
  },
  {
    field: 'issued_on',
    label: 'Fecha',
    type: 'date',
    from: invoice => invoice.issued_on,
    read: invoice => invoice.document?.read_issued_on,
  },
  {
    field: 'total',
    label: 'Monto',
    type: 'number',
    from: invoice => invoice.total,
    read: invoice => invoice.document?.read_total,
  },
]

/**
 * Las facturas que esperan una decisión, con lo que hace falta para tomarla.
 *
 * Dos preguntas distintas se contestan en la misma tarjeta, porque quien decide
 * las mira juntas: **qué dice** la factura y **de quién es**.
 *
 * Los tres datos de cabecera vienen cargados con lo que publicó el portal y con
 * lo que leyó el archivo al lado, para que corregir sea leer y elegir. Dejar un
 * campo como está es confirmarlo, y por eso confirmar no cuesta nada: es la
 * respuesta más frecuente (RF-31). Ninguno se completa por suposición — lo que
 * está escrito lo escribió el portal, y lo que el archivo dice se muestra
 * aparte, nunca aplicado solo.
 *
 * Antes de guardar una grafía la pantalla dice **cuántas facturas apartadas va a
 * resolver** (RF-48), y ese número lo cuenta la misma consulta que después las
 * resuelve: lo que se promete acá es lo que pasa.
 */
export function ReviewQueue({
  invoices,
  suppliers,
  canDecide,
}: {
  invoices: Invoice[]
  suppliers: Supplier[]
  canDecide: boolean
}) {
  const router = useRouter()
  const [chosen, setChosen] = useState<Record<number, number>>({})
  const [preview, setPreview] = useState<Record<number, string>>({})
  const [edited, setEdited] = useState<Record<number, InvoiceCorrections>>({})
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function look(invoice: Invoice, supplierId: number) {
    const result = await previewAlias(invoice.supplier_text, supplierId)
    if (result.ok) {
      setPreview({
        ...preview,
        [invoice.id]: `Guardar esta grafía resuelve ${result.data.invoices} factura${
          result.data.invoices === 1 ? '' : 's'
        }.`,
      })
    }
  }

  /** Lo que quedó distinto de lo que publicó el portal, y sólo eso. */
  function correctionsOf(invoice: Invoice): InvoiceCorrections {
    const typed = edited[invoice.id] ?? {}
    const corrections: InvoiceCorrections = {}
    for (const { field, from } of HEADER_FIELDS) {
      const value = typed[field]
      if (value !== undefined && value !== '' && value !== from(invoice)) {
        corrections[field] = value
      }
    }
    return corrections
  }

  async function decide(
    invoice: Invoice,
    supplierId: number | null,
    remember: boolean
  ): Promise<void> {
    setBusy(true)
    setError(null)
    // Una sola llamada para las dos decisiones. El endpoint de resolución ya
    // guarda la grafía y resuelve con ella las que estaban esperando cuando se
    // le pide recordar, así que encadenar dos llamadas sólo agregaría una
    // ventana en la que la corrección llega a una factura que la primera ya
    // sacó de la cola.
    const result = await resolveInvoice(invoice.id, supplierId, remember, correctionsOf(invoice))
    setBusy(false)
    if (result.ok) {
      router.refresh()
      return
    }
    setError(result.message)
  }

  if (invoices.length === 0) {
    return (
      <p className="rounded border border-dashed p-8 text-center text-muted-foreground">
        No quedó ninguna factura esperando una decisión.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {error && (
        <p className="rounded border border-danger-border bg-danger-surface p-3 text-sm text-danger">
          {error}
        </p>
      )}

      {invoices.map(invoice => {
        const selected = chosen[invoice.id] ?? 0
        return (
          <article key={invoice.id} className="space-y-3 rounded border p-4">
            <header className="flex flex-wrap items-baseline justify-between gap-2">
              <div>
                <h3 className="font-medium">
                  {invoice.number} · {money(invoice.total)}
                </h3>
                <p className="text-sm text-muted-foreground">
                  Llegó a nombre de «{invoice.supplier_text}» · {day(invoice.issued_on)}
                </p>
              </div>
              <p className="text-sm text-warn">{invoice.review_reason}</p>
            </header>

            {invoice.document && !invoice.document.agrees && (
              <div className="space-y-1 text-sm">
                <p className="text-muted-foreground">
                  Lo que dice el archivo:{' '}
                  <a
                    className="underline"
                    href={`/api/proxy/invoices/${invoice.id}/file`}
                    rel="noreferrer"
                    target="_blank"
                  >
                    abrir el original
                  </a>
                </p>
                <pre className="max-h-40 overflow-auto rounded bg-muted p-2 text-xs">
                  {invoice.document.excerpt || 'No se pudo leer.'}
                </pre>
              </div>
            )}

            {canDecide && (
              <div className="space-y-2">
                <div className="grid gap-3 sm:grid-cols-3">
                  {HEADER_FIELDS.map(({ field, label, type, from, read }) => {
                    const said = read(invoice)
                    return (
                      <label key={field} className="text-sm">
                        <span className="mb-1 block text-muted-foreground">{label}</span>
                        <input
                          className="w-full rounded border px-2 py-1"
                          type={type}
                          step={type === 'number' ? '0.01' : undefined}
                          value={edited[invoice.id]?.[field] ?? from(invoice)}
                          onChange={event =>
                            setEdited({
                              ...edited,
                              [invoice.id]: {
                                ...edited[invoice.id],
                                [field]: event.target.value,
                              },
                            })
                          }
                        />
                        <span className="mt-1 block text-xs text-muted-foreground">
                          {said ? `El archivo dice ${said}` : 'El archivo no lo dice'}
                        </span>
                      </label>
                    )
                  })}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <select
                    className="rounded border px-2 py-1 text-sm"
                    value={selected}
                    onChange={event => {
                      const supplierId = Number(event.target.value)
                      setChosen({ ...chosen, [invoice.id]: supplierId })
                      if (supplierId) void look(invoice, supplierId)
                    }}
                  >
                    <option value={0}>¿De qué proveedor es?</option>
                    {suppliers.map(supplier => (
                      <option key={supplier.id} value={supplier.id}>
                        {supplier.legal_name}
                      </option>
                    ))}
                  </select>
                  <Button
                    type="button"
                    disabled={busy || selected === 0}
                    onClick={() => void decide(invoice, selected, true)}
                  >
                    Guardar la grafía
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={busy || selected === 0}
                    onClick={() => void decide(invoice, selected, false)}
                  >
                    Sólo esta factura
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={busy}
                    onClick={() => void decide(invoice, null, false)}
                  >
                    Está bien así
                  </Button>
                </div>
                {preview[invoice.id] && (
                  <p className="text-sm text-muted-foreground">{preview[invoice.id]}</p>
                )}
              </div>
            )}
          </article>
        )
      })}
    </div>
  )
}
