import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { NoPermission } from '@/components/common/NoPermission'
import { SpellingList } from '@/components/purchases/SpellingList'
import { fetchFromApi } from '@/lib/api/server'
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
  const [aliases, suppliers, session] = await Promise.all([
    fetchFromApi<SupplierAlias[]>('/supplier-aliases'),
    fetchFromApi<SupplierList>('/suppliers'),
    getSession(),
  ])

  if (aliases === null || suppliers === null) {
    return <NoPermission what="el padrón de proveedores" />
  }

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
        suppliers={suppliers.items}
        canEdit={canEdit(session?.permissions ?? {}, 'SUPPLIERS')}
      />
    </main>
  )
}
