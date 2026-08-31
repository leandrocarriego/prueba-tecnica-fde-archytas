import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { CategoryList } from '@/components/categories/CategoryList'
import { NoPermission } from '@/components/common/NoPermission'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { CategoryList as CategoryListRead } from '@/lib/catalog/types'

export const metadata = {
  title: 'Rubros — Plataforma Cordillera',
}

/**
 * Los rubros del catálogo, con su conteo y cómo llegan escritos (H1 y H2).
 *
 * «Sin rubro» aparece como un grupo más y entra en el total: es lo que hace que
 * el corte cierre sin que nadie tenga que sumar aparte.
 */
export default async function CategoriesPage() {
  const [listing, session] = await Promise.all([
    fetchFromApi<CategoryListRead>('/categories'),
    getSession(),
  ])

  if (listing === null) {
    return <NoPermission what="los rubros del catálogo" />
  }

  return (
    <main className="mx-auto max-w-5xl space-y-8 p-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Rubros</h1>
        <p className="text-sm text-muted-foreground">
          Cada rubro con cuántos productos tiene y con todas las formas en que llega escrito.
        </p>
      </header>

      <nav className="flex gap-4 text-sm">
        <Link className="underline" href="/rubros/sin-clasificar">
          Productos sin rubro ({listing.unclassified_count})
        </Link>
        <Link className="underline" href="/rubros/equivalencias">
          Equivalencias guardadas
        </Link>
      </nav>

      <CategoryList
        listing={listing}
        canEdit={canEdit(session?.permissions ?? {}, 'PRODUCT_CATEGORIES')}
      />
    </main>
  )
}
