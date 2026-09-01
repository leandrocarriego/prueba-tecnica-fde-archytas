'use client'

import { useState } from 'react'

import { ResolvedSales } from '@/components/sales/ResolvedSales'
import { RuleList } from '@/components/triage/RuleList'
import type { ResolvedGroup } from '@/lib/sales/types'
import { sectionLabel, sectionOfKind, type Rule } from '@/lib/triage/types'

/** El orden en que se ofrecen las áreas, cuando hay más de una. */
const AREAS = ['PURCHASING', 'SALES', 'SYSTEM'] as const

/**
 * Todo lo que alguien ya decidió, en un solo lugar.
 *
 * Eran dos bloques al pie de la cola —las reglas aprendidas y las ventas
 * resueltas— y son la misma clase de cosa: **una decisión tomada, que se aplica
 * sola y que se puede revocar**. Tenerlas separadas obligaba a saber de antemano
 * en cuál de las dos buscar lo que se venía a deshacer, que es justo lo que no
 * se sabe cuando uno viene a deshacer algo.
 *
 * Las pestañas aparecen **sólo si hay más de un área con algo**. Una fila de
 * pestañas sobre una lista que no se puede filtrar de ninguna manera útil es un
 * control decorativo, y acá no hay ninguno: con decisiones de una sola área, la
 * lista se muestra y listo.
 *
 * El recorte por permisos no pasa por acá: lo hace el backend sobre los casos y
 * sobre las dos consultas que alimentan esto. Filtrar por área es una comodidad
 * para leer, nunca la restricción.
 */
export function SavedDecisions({ rules, sales }: { rules: Rule[]; sales: ResolvedGroup[] }) {
  const [area, setArea] = useState<string>('all')

  // Qué áreas tienen algo. Las ventas resueltas son de ventas por definición;
  // las reglas dicen su área por la clase de caso que resolvieron.
  const present = new Set<string>(rules.map(rule => sectionOfKind(rule.kind)))
  if (sales.length > 0) present.add('SALES')
  const tabs = AREAS.filter(one => present.has(one))

  const shownRules = area === 'all' ? rules : rules.filter(r => sectionOfKind(r.kind) === area)
  const shownSales = area === 'all' || area === 'SALES' ? sales : []

  return (
    <section className="space-y-4 rounded-xl border border-border bg-card p-6">
      <div className="space-y-1">
        <h2 className="text-lg font-semibold text-foreground">Decisiones guardadas</h2>
        <p className="text-sm text-muted-foreground">
          Lo que ya se decidió. El sistema aplica solo las reglas a los casos iguales; si dejás una
          sin efecto, esos casos vuelven a esta pantalla.
        </p>
      </div>

      {tabs.length > 1 && (
        <nav aria-label="Área de las decisiones" className="flex flex-wrap gap-2">
          {['all', ...tabs].map(id => (
            <button
              key={id}
              type="button"
              aria-pressed={id === area}
              onClick={() => setArea(id)}
              className={`cursor-pointer rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                id === area
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-input bg-card text-muted-foreground hover:bg-muted'
              }`}
            >
              {id === 'all' ? 'Todas' : sectionLabel(id)}
            </button>
          ))}
        </nav>
      )}

      {shownSales.length > 0 && (
        <div className="space-y-2">
          <h3 className="section-label">Ventas repetidas que alguien resolvió</h3>
          <ResolvedSales groups={shownSales} />
        </div>
      )}

      <div className="space-y-2">
        {shownSales.length > 0 && <h3 className="section-label">Reglas que el sistema aplica</h3>}
        <RuleList rules={shownRules} />
      </div>
    </section>
  )
}
