import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { SpellingList } from '@/components/purchases/SpellingList'
import { readFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { SupplierAlias, SupplierList } from '@/lib/purchases/types'

export const metadata = {
  title: 'Grafías de proveedores — Plataforma Cordillera',
}

/**
 * Cómo llega escrito el nombre de cada proveedor (H8 de 004).
 *
 * Veinticuatro grafías para ocho proveedores, medidas. Las que el sistema
 * reconoció solo dicen «observada»; las que decidió alguien dicen quién.
 */
export default async function SpellingsPage() {
  const [read, suppliers, session] = await Promise.all([
    readFromApi<SupplierAlias[]>('/supplier-aliases'),
    readFromApi<SupplierList>('/suppliers'),
    getSession(),
  ])

  if (!read.ok || !suppliers.ok) {
    // La lista de proveedores es tan necesaria como las grafías: sin ella no se
    // puede decir a quién quedó asignada ninguna. Si cualquiera de las dos fue
    // un rechazo, es un rechazo; si no, la API no contestó.
    const refused =
      (!read.ok && read.failure === 'unauthorized') ||
      (!suppliers.ok && suppliers.failure === 'unauthorized')
    if (refused) {
      return <NoPermission what="el padrón de proveedores" />
    }
    return (
      <main className="mx-auto max-w-4xl space-y-6 p-8">
        <h1 className="text-2xl font-bold">Grafías</h1>
        <p className="rounded border border-danger-border bg-danger-surface p-4 text-sm text-danger">
          No pudimos traer las grafías guardadas. Probá de nuevo en unos minutos.
        </p>
      </main>
    )
  }

  const aliases = read.data

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <Link className="text-sm text-muted-foreground underline" href="/proveedores">
        « Volver al padrón
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Grafías</h1>
        <p className="text-sm text-muted-foreground">
          {aliases.length} formas en que llega escrito el nombre de un proveedor.
        </p>
      </header>

      <SpellingList
        aliases={aliases}
        suppliers={suppliers.data.items}
        canEdit={canEdit(session?.permissions ?? {}, 'SUPPLIERS')}
      />
    </main>
  )
}
