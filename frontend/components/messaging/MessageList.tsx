'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { annotateMessage, assignMessage, resolveMessage } from '@/app/actions/messaging'
import { Button } from '@/components/ui/button'
import { formatMoment } from '@/lib/catalog/format'
import type { Assignee, Message } from '@/lib/messaging/types'

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
    return (
      <p className="rounded border border-dashed p-8 text-center text-muted-foreground">
        No hay mensajes que coincidan.
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

      {messages.map(message => (
        <article key={message.id} className="space-y-2 rounded border p-4">
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
            <p className="text-sm text-muted-foreground">{formatMoment(message.received_at)}</p>
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
            <p className="rounded border border-warn-border bg-warn-surface p-2 text-xs text-warn">
              El aviso por este mensaje no se pudo entregar: {message.alert_failure}
            </p>
          )}

          {message.note && <p className="rounded bg-muted p-2 text-sm">Nota: {message.note}</p>}

          <footer className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-muted-foreground">
              {message.state === 'RESOLVED' ? 'Resuelto' : 'Pendiente'}
            </span>
            {message.assignee_user_id !== null && (
              <span className="text-muted-foreground">
                A cargo de{' '}
                {assignees.find(person => person.user_id === message.assignee_user_id)?.name ??
                  `#${message.assignee_user_id}`}
              </span>
            )}
            {canEdit && message.state !== 'RESOLVED' && (
              <>
                <Button
                  type="button"
                  disabled={busy}
                  onClick={() => void run(() => resolveMessage(message.id))}
                >
                  Marcar resuelto
                </Button>
                <select
                  className="rounded border px-2 py-1 text-sm"
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
        </article>
      ))}
    </div>
  )
}
