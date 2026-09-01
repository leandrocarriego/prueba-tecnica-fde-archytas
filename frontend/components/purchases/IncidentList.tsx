'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

import { closeIncident } from '@/app/actions/purchases'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { formatMoment } from '@/lib/catalog/format'

import type { Incident } from '@/lib/purchases/types'
import { Empty } from '@/components/ui/state'
import { Day } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Notice } from '@/components/ui/notice'

/**
 * Los incidentes, y la única cosa que se hace con uno: cerrarlo diciendo qué
 * se hizo (RF-57 a RF-59).
 *
 * El motivo es obligatorio y por eso el botón espera a que haya texto: un
 * incidente que se cierra sin explicación es un incidente que se apaga, y la
 * regla firmada dice lo contrario. Cerrado, la tarjeta se queda: muestra el
 * motivo y cuándo, porque «deja de contarse» y «desaparece» no son lo mismo.
 */
export function IncidentList({ incidents }: { incidents: Incident[] }) {
  if (incidents.length === 0) {
    return (
      <Empty title="Nada por resolver.">
        Cuando una factura se pase de su fecha sin recibo, va a aparecer acá.
      </Empty>
    )
  }

  return (
    <div className="space-y-4">
      {incidents.map(incident => (
        <IncidentCard key={incident.id} incident={incident} />
      ))}
    </div>
  )
}

function IncidentCard({ incident }: { incident: Incident }) {
  const router = useRouter()
  const [resolution, setResolution] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function close() {
    setBusy(true)
    setError(null)
    const result = await closeIncident(incident.id, resolution)
    setBusy(false)
    if (result.ok) {
      router.refresh()
      return
    }
    setError(result.message)
  }

  const isClosed = incident.closed_at !== null

  return (
    <Card className="space-y-3 p-5">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-medium">
          <Link className="text-link hover:underline" href={`/facturas/${incident.invoice_id}`}>
            {incident.invoice_number ?? `Factura ${incident.invoice_id}`}
          </Link>
          {incident.supplier_name && (
            <span className="ml-2 font-normal text-muted-foreground">
              · {incident.supplier_name}
            </span>
          )}
        </h3>
        <span className="flex items-center gap-2 text-sm text-muted-foreground">
          Vencida el <Day value={incident.opened_on} />
          {/* El estado del incidente, dicho como estado (`RF-06`). */}
          <Badge tone={isClosed ? 'ok' : 'warn'}>{isClosed ? 'Cerrado' : 'Abierto'}</Badge>
        </span>
      </header>

      {isClosed ? (
        <div className="space-y-1 text-sm">
          <p>{incident.resolution}</p>
          {/*
            RF-58 pide además **quién** lo cerró, y acá viaja un
            `closed_by_user_id` que a nadie le dice nada. Escribir "por el
            usuario 3" no cumple el requisito, lo simula. El nombre lo resuelve
            la tarea 29, que le da a los cuatro requisitos de 005 que piden un
            nombre el mismo tratamiento que la 004 ya le dio a la factura
            apartada (`resolved_by_name`, con `ActorDirectory`).
          */}
          <p className="text-muted-foreground">Cerrado el {formatMoment(incident.closed_at)}</p>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <Input
            className="min-w-64 flex-1"
            placeholder="Qué se hizo al respecto"
            value={resolution}
            onChange={event => setResolution(event.target.value)}
          />
          <Button
            type="button"
            disabled={busy || resolution.trim() === ''}
            onClick={() => void close()}
          >
            Cerrar el incidente
          </Button>
        </div>
      )}

      {error && <Notice tone="danger" title={error} />}
    </Card>
  )
}
