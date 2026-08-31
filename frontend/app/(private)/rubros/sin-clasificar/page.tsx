import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { UnclassifiedQueue } from '@/components/categories/UnclassifiedQueue'
import { NoPermission } from '@/components/common/NoPermission'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { CategoryList, UnclassifiedList } from '@/lib/catalog/types'

export const metadata = {
  title: 'Productos sin rubro — Plataforma Cordillera',
}

/**
 * La cola de productos sin rubro, con la propuesta del sistema (H2 y H3).
 *
 * Mientras nadie confirma, el producto **es** «sin rubro»: cuenta como tal, va
 * en los totales y sigue en esta lista (RF-16). Por eso la propuesta se muestra
 * y no se guarda en ningún lado.
 */
export default async function UnclassifiedPage() {
  const [queue, categories, session] = await Promise.all([
    fetchFromApi<UnclassifiedList>('/categories/unclassified?limit=200'),
    fetchFromApi<CategoryList>('/categories'),
    getSession(),
  ])

  if (queue === null || categories === null) {
    return <NoPermission what="los rubros del catálogo" />
  }

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-8">
      <Link className="text-sm text-muted-foreground underline" href="/rubros">
        « Volver a los rubros
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Productos sin rubro</h1>
        <p className="text-sm text-muted-foreground">
          {queue.total === 0
            ? 'No quedó ninguno sin clasificar.'
            : `${queue.total} ${queue.total === 1 ? 'producto espera' : 'productos esperan'} un rubro.`}
        </p>
      </header>

      <UnclassifiedQueue
        queue={queue}
        categories={categories.items}
        canEdit={canEdit(session?.permissions ?? {}, 'PRODUCT_CATEGORIES')}
      />
    </main>
  )
}
