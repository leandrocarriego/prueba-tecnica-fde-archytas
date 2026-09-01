'use client'

import { useState } from 'react'

import type { UserRead } from '@/app/actions/access'
import { AccessTable } from '@/components/access/AccessTable'
import { NewAccessForm } from '@/components/access/NewAccessForm'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Notice } from '@/components/ui/notice'
import { Empty } from '@/components/ui/state'

/**
 * Usuarios y permisos: la tarjeta entera de la pantalla (`docs/design/` 3m).
 *
 * El alta se pide con un botón y se abre acá adentro, en vez de vivir siempre
 * desplegada arriba de la tabla: lo que se viene a hacer a esta pantalla casi
 * siempre es mirar quién entra, y dar de alta es la excepción. El botón es de
 * tinta —abrir un formulario no es la decisión, es el camino hacia ella— y el
 * único naranja sigue siendo el que da de alta de verdad (`UI-05`).
 *
 * Client Component porque esa apertura es estado, y porque la tabla ya lo era.
 */
export function AccessPanel({ accesses, viewerId }: { accesses: UserRead[]; viewerId: number }) {
  const [inviting, setInviting] = useState(false)
  const [created, setCreated] = useState<string | null>(null)

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 p-5">
        <div>
          <h2 className="font-semibold">Usuarios y permisos</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Sólo el dueño accede a esta pantalla.
          </p>
        </div>
        <Button
          type="button"
          onClick={() => {
            setCreated(null)
            setInviting(open => !open)
          }}
        >
          {inviting ? 'Cerrar' : 'Invitar persona'}
        </Button>
      </div>

      {/* El alta que sale bien cierra el formulario y deja dicho acá que salió
          bien: adentro del formulario, el aviso se iba con él. */}
      {created && (
        <div className="border-t border-border p-5">
          <Notice tone="ok" title={created} />
        </div>
      )}

      {inviting && (
        <div className="border-t border-border p-5">
          <NewAccessForm
            onCreated={message => {
              setCreated(message)
              setInviting(false)
            }}
          />
        </div>
      )}

      {accesses.length === 0 ? (
        <div className="border-t border-border p-5">
          <Empty title="Todavía no hay ningún acceso además del tuyo." />
        </div>
      ) : (
        <AccessTable accesses={accesses} viewerId={viewerId} />
      )}

      <p className="border-t border-border bg-muted p-4 text-sm text-muted-foreground">
        Lo que un rol no puede ver no aparece en el menú: no es un botón que devuelve error.
      </p>
    </Card>
  )
}
