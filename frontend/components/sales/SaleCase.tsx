'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { correctSale, resolveSaleGroup } from '@/app/actions/sales'
import { SaleCorrection } from '@/components/sales/SaleCorrection'
import { CaseHeader } from '@/components/triage/CaseHeader'
import { Code, Day, Money } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Notice } from '@/components/ui/notice'
import { useToast } from '@/components/ui/toast'
import { count } from '@/lib/format'
import type { ReviewQueue, Sale, SaleGroup } from '@/lib/sales/types'
import type { Case } from '@/lib/triage/types'
import { isUnconfirmedSale, pill, saleTone } from '@/lib/ui/tone'

/** Cómo se nombra en pantalla cada campo en el que dos versiones difieren. */
const FIELDS: Record<string, string> = {
  sold_on: 'la fecha',
  product_code: 'el producto',
  quantity: 'la cantidad',
  total: 'el total',
}

/** Las dos clases de caso que resuelve este panel y no el genérico. */
export const SALE_CASE_KINDS: readonly string[] = ['repeated_sale', 'broken_sale']

/** La llave con la que el caso se abrió: el código agrupador, o el id del registro. */
function keyOf(item: Case): string {
  const value = item.payload.key
  return typeof value === 'string' ? value : ''
}

/**
 * Una venta apartada, resuelta en la cola donde está todo lo demás.
 *
 * Dos clases de caso y dos decisiones distintas, que es la razón por la que
 * este panel existe en vez de ser dos opciones más del genérico:
 *
 * - **Repetida**: dos o más versiones de la misma venta que no coinciden.
 *   Se muestran una al lado de la otra con los campos en que difieren
 *   señalados (RF-30 de 009), y se elige cuál vale — o se declara que nunca
 *   fueron la misma venta.
 * - **Rota**: le falta un dato, o apunta a un producto que no existe. Se
 *   completa acá, y lo que el portal informó se conserva al lado (RF-41).
 *
 * Ninguna de las dos se contesta eligiendo entre opciones escritas de antemano
 * ni se guarda como regla: la próxima venta rota es otra venta, y elegir entre
 * dos versiones es una discusión sobre un registro y no sobre una clase de caso.
 * Por eso tampoco hay pasos: el caso ya es la pregunta.
 *
 * **La cabeza es la misma que la de los demás casos** (`CaseHeader`), y eso no
 * es una economía: quien recorre la cola tiene que ver lo mismo arriba en todos,
 * o la pantalla se lee como dos pantallas pegadas.
 */
export function SaleCase({
  item,
  queue,
  mayResolve,
}: {
  item: Case
  /** La cola de ventas, o `null` si quien mira no la alcanza. */
  queue: ReviewQueue | null
  mayResolve: boolean
}) {
  const router = useRouter()
  const { addToast } = useToast()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const key = keyOf(item)
  const group: SaleGroup | null =
    item.kind === 'repeated_sale' ? (queue?.groups.find(one => one.code_key === key) ?? null) : null
  const sale: Sale | null =
    item.kind === 'broken_sale' ? (queue?.broken.find(one => String(one.id) === key) ?? null) : null

  async function run(action: () => Promise<{ ok: boolean; message?: string }>, done: string) {
    setBusy(true)
    setError(null)
    const result = await action()
    setBusy(false)
    if (result.ok) {
      addToast({
        type: 'success',
        title: 'Venta resuelta',
        description: done,
      })
      router.refresh()
      return
    }
    setError(result.message ?? 'No se pudo guardar')
  }

  return (
    <div className="flex h-full flex-col gap-5 rounded-xl border border-border bg-card p-6">
      <CaseHeader item={item} />

      {error && <Notice tone="danger" title={error} />}

      {/*
        Quien no alcanza las ventas ve el caso y no el registro: la cola le
        muestra el área que sí alcanza (RF-12), pero los datos de la venta están
        detrás de `SALES`. Se lo dice, en vez de dibujar un panel vacío que
        parezca un error de la pantalla.
      */}
      {queue === null ? (
        <p className="text-sm text-muted-foreground">
          {mayResolve
            ? // Alcanza el área y la cola no vino igual: es una caída, y se dice
              // como tal. Mandarlo a pedir un permiso que ya tiene sería culpar
              // a una persona por algo que le pasó al backend.
              'No pudimos traer los datos de esta venta. Probá de nuevo en un momento.'
            : 'Esta venta la resuelve quien trabaja en ventas. El caso se va a ir solo de la cola cuando alguien la decida.'}
        </p>
      ) : group !== null ? (
        <RepeatedSale
          group={group}
          busy={busy}
          mayResolve={mayResolve}
          onKeep={version =>
            void run(
              () => resolveSaleGroup(group.code_key, 'keep', version),
              'Queda una sola versión sumando.'
            )
          }
          onDistinct={() =>
            void run(
              () => resolveSaleGroup(group.code_key, 'distinct', null),
              'Las dos ventas suman.'
            )
          }
        />
      ) : sale !== null ? (
        <BrokenSale
          sale={sale}
          busy={busy}
          mayResolve={mayResolve}
          onCorrect={(values, isEstimated) =>
            void run(
              () => correctSale(sale.id, values, isEstimated),
              'La venta quedó corregida y vuelve a los indicadores.'
            )
          }
        />
      ) : (
        /*
          El caso está abierto y la venta ya no espera nada. Pasa cuando alguien
          la resolvió desde otra pestaña: el caso se cierra solo con el evento
          que publica `sales`, y lo único que falta acá es refrescar.
        */
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Esta venta ya no está esperando una decisión. Alguien la resolvió mientras tenías la
            pantalla abierta.
          </p>
          <Button type="button" variant="outline" onClick={() => router.refresh()}>
            Actualizar la cola
          </Button>
        </div>
      )}
    </div>
  )
}

/** Las versiones enfrentadas, y las dos salidas (RF-30 a RF-32 de 009). */
function RepeatedSale({
  group,
  busy,
  mayResolve,
  onKeep,
  onDistinct,
}: {
  group: SaleGroup
  busy: boolean
  mayResolve: boolean
  onKeep: (saleId: number) => void
  onDistinct: () => void
}) {
  const differences = (group.differences ?? []).map(field => FIELDS[field] ?? field)

  return (
    <section className="space-y-4">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-foreground">
          Código {group.versions[0]?.code}: {group.versions.length} versiones
        </h3>
        <p className="text-sm text-warn">
          {differences.length === 0
            ? 'Difieren en algún dato. Ninguna suma mientras tanto.'
            : `Difieren en ${differences.join(', ')}. Ninguna suma mientras tanto.`}
        </p>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted">
              <th className="section-label px-3 py-2 text-left">Fecha</th>
              <th className="section-label px-3 py-2 text-left">Producto</th>
              <th className="section-label px-3 py-2 text-right">Cantidad</th>
              <th className="section-label px-3 py-2 text-right">Total</th>
              {mayResolve && <th className="px-3 py-2" />}
            </tr>
          </thead>
          <tbody>
            {group.versions.map(version => (
              <tr key={version.id} className="border-b border-border last:border-0">
                <Day value={version.sold_on} cell className="px-3 py-2 text-left" />
                <Code value={version.product_code} cell className="px-3 py-2 text-left" />
                <td className="amount px-3 py-2 text-right">{count(version.quantity)}</td>
                <td className="px-3 py-2 text-right">
                  <Money value={version.total} as="span" />
                  {/*
                    `RF-08`: una venta apartada o estimada no está confirmada, y
                    se ve punteada sin leer la etiqueta.
                  */}
                  <Badge
                    className="ml-2"
                    tone={pill(saleTone(version.state), isUnconfirmedSale(version))}
                  >
                    {version.is_estimated ? 'Estimada' : 'Apartada'}
                  </Badge>
                </td>
                {mayResolve && (
                  <td className="px-3 py-2 text-right">
                    <Button
                      type="button"
                      variant="outline"
                      disabled={busy}
                      onClick={() => onKeep(version.id)}
                    >
                      Ésta es la válida
                    </Button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {mayResolve && (
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" variant="outline" disabled={busy} onClick={onDistinct}>
            Son ventas distintas
          </Button>
          <p className="text-xs text-muted-foreground">
            Si nunca fueron la misma venta, las dos vuelven a sumar y el código que comparten es el
            error.
          </p>
        </div>
      )}
    </section>
  )
}

/** El registro roto, con lo que el portal dijo y el formulario que lo completa. */
function BrokenSale({
  sale,
  busy,
  mayResolve,
  onCorrect,
}: {
  sale: Sale
  busy: boolean
  mayResolve: boolean
  onCorrect: (
    values: { sold_on?: string; product_code?: string; quantity?: number; total?: string },
    isEstimated: boolean
  ) => void
}) {
  return (
    <section className="space-y-4">
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground">Qué trajo el portal</h3>
        <dl className="grid gap-4 rounded-lg border border-border bg-muted p-4 sm:grid-cols-2">
          <div className="min-w-0">
            <dt className="section-label">Código</dt>
            <dd className="mt-1.5 text-sm">
              <Code value={sale.code} />
            </dd>
          </div>
          <div className="min-w-0">
            <dt className="section-label">Fecha</dt>
            <dd className="mt-1.5 text-sm">
              <Day value={sale.sold_on} />
            </dd>
          </div>
          <div className="min-w-0">
            <dt className="section-label">Producto</dt>
            <dd className="mt-1.5 text-sm">
              <Code value={sale.product_code} />
            </dd>
          </div>
          <div className="min-w-0">
            <dt className="section-label">Total</dt>
            <dd className="mt-1.5 text-sm">
              <Money value={sale.total} as="span" />
            </dd>
          </div>
        </dl>
      </div>

      {mayResolve ? (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-foreground">Completá lo que falta</h3>
          <p className="text-xs text-muted-foreground">
            Lo que el portal informó se guarda igual, pase lo que pase con la corrección. Si un
            valor no se puede saber, marcalo como estimado: todo indicador que sume esta venta lo va
            a decir.
          </p>
          <SaleCorrection sale={sale} disabled={busy} onSubmit={onCorrect} />
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Corregir una venta es de quien trabaja en ventas. Pedísela a quien lleva el área.
        </p>
      )}
    </section>
  )
}
