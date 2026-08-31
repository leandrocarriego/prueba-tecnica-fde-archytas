import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { MessageList } from '@/components/messaging/MessageList'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { MessageList as MessageListRead } from '@/lib/messaging/types'

export const metadata = {
  title: 'Mensajes — Plataforma Cordillera',
}

interface PageProps {
  searchParams: Promise<{ tipo?: string; estado?: string }>
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

  const [listing, session] = await Promise.all([
    fetchFromApi<MessageListRead>(`/messages?${query.toString()}`),
    getSession(),
  ])

  if (listing === null) {
    return <NoPermission what="la bandeja de mensajes" />
  }

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Mensajes</h1>
        <p className="text-sm text-muted-foreground">
          {listing.pending} sin resolver de {listing.total} en esta vista.
        </p>
      </header>

      <nav className="flex flex-wrap gap-4 text-sm">
        <Link className="underline" href="/mensajes">
          Todos
        </Link>
        <Link className="underline" href="/mensajes?estado=PENDING">
          Pendientes
        </Link>
        <Link className="underline" href="/mensajes?tipo=PAYMENT_CLAIM">
          Reclamos de pago
        </Link>
        <Link className="underline" href="/mensajes?tipo=DUE_SOON">
          Vencimientos
        </Link>
        <Link className="underline" href="/mensajes?tipo=LOW_STOCK">
          Stock bajo
        </Link>
        <Link className="underline" href="/mensajes?tipo=UNCLASSIFIED">
          Sin clasificar
        </Link>
      </nav>

      <MessageList
        messages={listing.items}
        canEdit={canEdit(session?.permissions ?? {}, 'SUPPLIER_MESSAGES')}
      />
    </main>
  )
}
