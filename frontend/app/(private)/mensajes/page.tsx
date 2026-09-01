import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { MessageList } from '@/components/messaging/MessageList'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { Assignee, MessageList as MessageListRead } from '@/lib/messaging/types'
import { Button } from '@/components/ui/button'
import { selectClassName } from '@/components/ui/input'

export const metadata = {
  title: 'Mensajes — Plataforma Cordillera',
}

interface PageProps {
  searchParams: Promise<{ tipo?: string; estado?: string; proveedor?: string }>
}

/**
 * La bandeja del portal, en un lugar donde el equipo sí entra (H4 y H5 de 007).
 *
 * El problema no era la bandeja: era que vivía adentro de un sistema al que
 * nadie entra. Por eso esta pantalla existe, y por eso los avisos importantes
 * además salen por WhatsApp en vez de quedarse acá esperando.
 */
export default async function MessagesPage({ searchParams }: PageProps) {
  const filters = await searchParams
  const query = new URLSearchParams({ limit: '200' })
  if (filters.tipo) query.set('kind', filters.tipo)
  if (filters.estado) query.set('state', filters.estado)
  // RF-26: por tipo, por estado **y por proveedor**. El criterio firmado pide
  // «los reclamos pendientes de un proveedor», que son los tres a la vez.
  if (filters.proveedor) query.set('supplier_name', filters.proveedor)

  // Quiénes pueden hacerse cargo de un mensaje (RF-30). Sale de la matriz de
  // permisos y no de una lista de roles escrita en el frontend: quien alcanza
  // esta sección en escritura es exactamente quien puede ser responsable, y
  // Julián no está entre ellos.
  const [listing, assignees, senders, session] = await Promise.all([
    fetchFromApi<MessageListRead>(`/messages?${query.toString()}`),
    fetchFromApi<Assignee[]>('/messages/assignees'),
    // El padrón como lo guarda `messaging`: son exactamente los valores que
    // `supplier_name` puede tomar, así que el filtro no ofrece nombres que no
    // encuentran nada.
    fetchFromApi<string[]>('/messages/senders'),
    getSession(),
  ])

  if (listing === null) {
    return <NoPermission what="la bandeja de mensajes" />
  }

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Mensajes</h1>
        <p className="text-sm text-muted-foreground">
          {listing.pending} sin resolver de {listing.total} en esta vista.
        </p>
      </header>

      <nav className="flex flex-wrap gap-4 text-sm">
        <Link className="text-link hover:underline" href="/mensajes">
          Todos
        </Link>
        <Link className="text-link hover:underline" href="/mensajes?estado=PENDING">
          Pendientes
        </Link>
        <Link className="text-link hover:underline" href="/mensajes?tipo=PAYMENT_CLAIM">
          Reclamos de pago
        </Link>
        <Link className="text-link hover:underline" href="/mensajes?tipo=DUE_SOON">
          Vencimientos
        </Link>
        <Link className="text-link hover:underline" href="/mensajes?tipo=LOW_STOCK">
          Stock bajo
        </Link>
        <Link className="text-link hover:underline" href="/mensajes?tipo=UNCLASSIFIED">
          Sin clasificar
        </Link>
      </nav>

      {/*
        Un form con GET, como en las órdenes: el filtro por proveedor es otra
        query sobre la misma pantalla, y el tipo y el estado que ya estaban
        puestos viajan en campos ocultos en vez de perderse al elegir.
      */}
      <form action="/mensajes" className="flex flex-wrap items-center gap-2 text-sm" method="get">
        {filters.tipo && <input name="tipo" type="hidden" value={filters.tipo} />}
        {filters.estado && <input name="estado" type="hidden" value={filters.estado} />}
        <label htmlFor="proveedor">Proveedor</label>
        <select
          className={selectClassName}
          defaultValue={filters.proveedor ?? ''}
          id="proveedor"
          name="proveedor"
        >
          <option value="">Todos</option>
          {(senders ?? []).map(name => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        {/* Filtrar no es la tarea: leer el buzón lo es (`RF-11`). */}
        <Button type="submit" variant="outline">
          Filtrar
        </Button>
      </form>

      <MessageList
        messages={listing.items}
        assignees={assignees ?? []}
        canEdit={canEdit(session?.permissions ?? {}, 'SUPPLIER_MESSAGES')}
      />
    </div>
  )
}
