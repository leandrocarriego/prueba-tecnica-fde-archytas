'use client'

import { useState } from 'react'

import { CaseDetail } from '@/components/triage/CaseDetail'
import { Badge } from '@/components/ui/badge'
import type { Category } from '@/lib/catalog/types'
import type { Supplier } from '@/lib/purchases/types'
import { caseKindLabel, sectionLabel, type Case } from '@/lib/triage/types'

/**
 * Los órdenes que la cola ofrece, y que hacen algo.
 *
 * El backend entrega los casos del más nuevo al más viejo, así que ése es el
 * primero de la lista y el que no reordena nada. Los otros tres contestan las
 * preguntas con las que alguien se sienta a vaciar esto: **qué está esperando
 * hace más**, **qué ya se pasó de plazo** y **qué se puede resolver de corrido**
 * porque es todo lo mismo.
 *
 * Ordenar es del navegador y no del backend porque la página ya trajo los casos
 * enteros: pedir de nuevo cien filas para verlas en otro orden sería un viaje
 * por algo que ya está acá.
 */
const ORDERS = {
  newest: {
    label: 'Más nuevos',
    compare: (a: Case, b: Case) => b.created_at.localeCompare(a.created_at),
  },
  oldest: {
    label: 'Más viejos',
    compare: (a: Case, b: Case) => a.created_at.localeCompare(b.created_at),
  },
  stale: {
    label: 'Demorados',
    compare: (a: Case, b: Case) =>
      Number(b.is_stale) - Number(a.is_stale) || a.created_at.localeCompare(b.created_at),
  },
  kind: {
    label: 'Por tipo',
    compare: (a: Case, b: Case) =>
      caseKindLabel(a.kind).localeCompare(caseKindLabel(b.kind)) ||
      sectionLabel(a.section).localeCompare(sectionLabel(b.section)) ||
      a.created_at.localeCompare(b.created_at),
  },
} as const

type Order = keyof typeof ORDERS

interface CaseQueueProps {
  items: Case[]
  /** Cuántos hay pendientes en total, que puede ser más de los que trajo la página. */
  pendingTotal: number
  mayCorrect: boolean
  categories: Category[]
  /** El padrón, para cargar a mano una factura o una orden. Vacío si no se alcanza. */
  suppliers: Supplier[]
}

/**
 * La cola y el caso abierto, uno al lado del otro (guía visual `3d`).
 *
 * Es el cambio de forma que la pantalla pedía: hasta acá los pendientes se
 * apilaban como tarjetas, cada una con todo su detalle abierto, y con doce
 * casos eso son doce pantallas de scroll para encontrar el que se vino a
 * resolver. El diseño firmado los pone en una lista angosta a la izquierda —el
 * tipo de caso y su motivo en un renglón— y abre uno solo a la derecha.
 *
 * **La selección vive acá y no en la barra de direcciones.** La página ya trajo
 * los cien casos con su `payload`, así que elegir otro no necesita ir al
 * servidor: es instantáneo. Y el caso que se estaba mirando puede desaparecer
 * —se resolvió, o alguien lo resolvió del otro lado y la página se refrescó—,
 * así que la selección se deriva de la lista en vez de guardarse: si el id ya no
 * está, se abre el primero del orden elegido.
 *
 * `key` sobre el detalle es lo que hace que cambiar de caso no arrastre lo
 * escrito en el anterior: un precio a medio tipear o un rubro elegido son
 * estado del caso que se estaba resolviendo, no del panel.
 */
export function CaseQueue({
  items,
  pendingTotal,
  mayCorrect,
  categories,
  suppliers,
}: CaseQueueProps) {
  const [openId, setOpenId] = useState<number | null>(null)
  const [order, setOrder] = useState<Order>('newest')
  // Una copia: `sort` ordena en el lugar, y el lugar es el arreglo que mandó la
  // página.
  const sorted = [...items].sort(ORDERS[order].compare)
  const current = sorted.find(item => item.id === openId) ?? sorted[0] ?? null

  if (current === null) return null

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
      <div className="w-full flex-none overflow-hidden rounded-xl border border-border bg-card lg:w-76">
        <p className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
          {/*
            Lo que hay en la lista, y cuántos son en total cuando la página no
            los trajo a todos: decir «12 pendientes» arriba de una lista de 100
            de 150 sería el único número de esta pantalla que no se puede
            verificar mirándola.
          */}
          <span className="section-label">
            {items.length} {items.length === 1 ? 'pendiente' : 'pendientes'}
            {pendingTotal > items.length && ` de ${pendingTotal}`}
          </span>

          {/*
            «Ordenar» de la guía visual, con órdenes que ordenan de verdad. Es un
            `select` nativo y no un menú propio: el navegador lo dibuja mejor, en
            un teléfono es el único que se usa cómodo, y acá alcanza.
          */}
          <select
            aria-label="Ordenar"
            className="section-label cursor-pointer bg-transparent text-link focus-visible:outline-none"
            value={order}
            onChange={event => setOrder(event.target.value as Order)}
          >
            {Object.entries(ORDERS).map(([id, option]) => (
              <option key={id} value={id}>
                {option.label}
              </option>
            ))}
          </select>
        </p>
        <ul className="max-h-[32rem] divide-y divide-border overflow-y-auto">
          {sorted.map(item => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => setOpenId(item.id)}
                aria-current={item.id === current.id ? 'true' : undefined}
                className={`block w-full cursor-pointer px-4 py-3 text-left hover:bg-muted ${
                  item.id === current.id ? 'border-l-[3px] border-brand bg-background' : ''
                }`}
              >
                <span className="flex items-start justify-between gap-2">
                  <span className="text-sm font-semibold text-foreground">
                    {caseKindLabel(item.kind)}
                  </span>
                  {item.is_stale && <Badge tone="warn">Demorado</Badge>}
                </span>
                <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">
                  {item.reason}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="min-w-0 flex-1">
        <CaseDetail
          key={current.id}
          item={current}
          mayCorrect={mayCorrect}
          categories={categories}
          suppliers={suppliers}
        />
      </div>
    </div>
  )
}
