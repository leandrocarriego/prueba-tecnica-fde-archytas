'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { annotateMessage, assignMessage, resolveMessage } from '@/app/actions/messaging'
import { Button } from '@/components/ui/button'
import { formatMoment } from '@/lib/catalog/format'
import type { Assignee, Message } from '@/lib/messaging/types'
import { Empty } from '@/components/ui/state'
import { Notice } from '@/components/ui/notice'
import { Code } from '@/components/ui/amount'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { selectClassName } from '@/components/ui/input'
import { messageTone } from '@/lib/ui/tone'

const KINDS: Record<string, string> = {
  PAYMENT_CLAIM: 'Reclamo de pago',
  DUE_SOON: 'Vencimiento próximo',
  LOW_STOCK: 'Stock bajo',
  UNCLASSIFIED: 'Sin clasificar',
}

/**
 * La bandeja del portal, fuera del portal.
 *
 * Un mensaje cuyo tipo el sistema no reconoce se muestra **sin clasificar** en
 * vez de descartarse (RF-25), y uno cuyo remitente no se identificó se muestra
 * diciéndolo (RF-24). Las dos cosas son lo mismo: se ve lo que hay, y se ve
 * hasta dónde se sabe.
 */
export function MessageList({
  messages,
  assignees,
  canEdit,
}: {
  messages: Message[]
  /**
   * Quiénes pueden hacerse cargo de un mensaje (RF-30). Los pasa la pantalla y
   * salen de la matriz: **cada pendiente tiene un dueño**, porque un mensaje sin
   * responsable es un mensaje que nadie va a resolver.
   */
  assignees: Assignee[]
  canEdit: boolean
}) {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function run(action: () => Promise<{ ok: boolean; message?: string }>) {
    setBusy(true)
    setError(null)
    const result = await action()
    setBusy(false)
    if (result.ok) {
      router.refresh()
      return
    }
    setError(result.message ?? 'No se pudo guardar')
  }

  if (messages.length === 0) {
    return <Empty title="No hay mensajes que coincidan." />
  }

  return (
    <div className="space-y-3">
      {error && <Notice tone="danger" title={error} />}

      {messages.map(message => (
        <Card key={message.id} className="space-y-2 p-5">
          <header className="flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <p className="text-sm text-muted-foreground">
                {KINDS[message.kind] ?? message.kind}
                {message.kind === 'UNCLASSIFIED' && message.kind_text
                  ? ` · el portal lo llama «${message.kind_text}»`
                  : ''}
              </p>
              <h3 className="font-medium">{message.subject}</h3>
            </div>
            <Code
              value={formatMoment(message.received_at)}
              as="div"
              className="text-sm text-muted-foreground"
            />
          </header>

          <p className="text-sm">
            {message.sender_unidentified ? (
              <span className="text-warn">
                {message.sender_text} · no pudimos identificar al remitente en el padrón
              </span>
            ) : (
              message.supplier_name
            )}
          </p>

          {message.body && <p className="text-sm text-muted-foreground">{message.body}</p>}

          {message.alert_failure && (
            <Notice tone="warn" title="El aviso por este mensaje no se pudo entregar">
              {message.alert_failure}
            </Notice>
          )}

          {message.note && <p className="rounded bg-muted p-2 text-sm">Nota: {message.note}</p>}

          <footer className="flex flex-wrap items-center gap-2 text-sm">
            {/* El estado del mensaje, del mapa único (`RF-06`). */}
            <Badge tone={messageTone(message.state)}>
              {message.state === 'RESOLVED' ? 'Resuelto' : 'Pendiente'}
            </Badge>
            {message.assignee_user_id !== null && (
              <span className="text-muted-foreground">
                A cargo de{' '}
                {assignees.find(person => person.user_id === message.assignee_user_id)?.name ??
                  `#${message.assignee_user_id}`}
              </span>
            )}
            {canEdit && message.state !== 'RESOLVED' && (
              <>
                {/*
                  Resolver es la tarea de esta pantalla, y es la única acción de
                  acento (`RF-11`): elegir responsable es un `select`.
                */}
                <Button
                  type="button"
                  variant="brand"
                  disabled={busy}
                  onClick={() => void run(() => resolveMessage(message.id))}
                >
                  Marcar resuelto
                </Button>
                <select
                  className={selectClassName}
                  value={message.assignee_user_id === null ? '' : String(message.assignee_user_id)}
                  disabled={busy}
                  onChange={event =>
                    void run(() =>
                      assignMessage(
                        message.id,
                        event.target.value === '' ? null : Number(event.target.value)
                      )
                    )
                  }
                >
                  <option value="">Sin responsable</option>
                  {assignees.map(person => (
                    <option key={person.user_id} value={String(person.user_id)}>
                      {person.name}
                    </option>
                  ))}
                </select>
                <Button
                  type="button"
                  variant="outline"
                  disabled={busy}
                  onClick={() => {
                    const note = window.prompt('Nota sobre este mensaje', message.note ?? '')
                    if (note) void run(() => annotateMessage(message.id, note))
                  }}
                >
                  Anotar
                </Button>
              </>
            )}
          </footer>
        </Card>
      ))}
    </div>
  )
}
