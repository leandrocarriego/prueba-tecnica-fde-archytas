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
 *
 * **Los mantiene compras, y ventas los consulta** (010). No hay ningún rol
 * escrito acá: las acciones se ofrecen según lo que la matriz de permisos diga
 * de esta sección, que es el mismo lugar donde el backend decide el 403.
 * Esconder un botón nunca fue el mecanismo — es una comodidad sobre él.
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
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Rubros</h1>
        <p className="text-sm text-muted-foreground">
          Cada rubro con cuántos productos tiene y con todas las formas en que llega escrito.
        </p>
      </header>

      <nav className="flex gap-4 text-sm">
        <Link className="text-link hover:underline" href="/rubros/sin-clasificar">
          Productos sin rubro ({listing.unclassified_count})
        </Link>
        <Link className="text-link hover:underline" href="/rubros/equivalencias">
          Equivalencias guardadas
        </Link>
        {/* RF-26: los que esperan que alguien decida su forma escrita. No son
            todos los «sin rubro» — por eso el número va aparte y lleva a la
            cola de revisión, que es donde se decide. */}
        <Link className="text-link hover:underline" href="/revision">
          Pendientes de revisión ({listing.pending_review_count})
        </Link>
      </nav>

      <CategoryList
        listing={listing}
        canEdit={canEdit(session?.permissions ?? {}, 'PRODUCT_CATEGORIES')}
      />
    </div>
  )
}
