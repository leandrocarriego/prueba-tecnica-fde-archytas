'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { previewAlias, resolveInvoice, saveAlias } from '@/app/actions/purchases'
import { Button } from '@/components/ui/button'
import { day, money } from '@/lib/format'
import type { Invoice, Supplier } from '@/lib/purchases/types'

/**
 * Las facturas que esperan una decisión, con lo que hace falta para tomarla.
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

  async function decide(
    invoice: Invoice,
    supplierId: number | null,
    remember: boolean
  ): Promise<void> {
    setBusy(true)
    setError(null)
    const result =
      remember && supplierId !== null
        ? await saveAlias(invoice.supplier_text, supplierId)
        : await resolveInvoice(invoice.id, supplierId, false)
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
        <p className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-900">{error}</p>
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
              <p className="text-sm text-amber-800">{invoice.review_reason}</p>
            </header>

            {invoice.document && !invoice.document.agrees && (
              <div className="space-y-1 text-sm">
                <p className="text-muted-foreground">Lo que dice el archivo:</p>
                <pre className="max-h-40 overflow-auto rounded bg-gray-50 p-2 text-xs">
                  {invoice.document.excerpt || 'No se pudo leer.'}
                </pre>
              </div>
            )}

            {canDecide && (
              <div className="space-y-2">
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
