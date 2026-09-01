import { getSession } from '@/app/actions/auth'
import { RubroNormalizer } from '@/components/catalog/RubroNormalizer'
import { NoPermission } from '@/components/common/NoPermission'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { CategoryList as CategoryListRead } from '@/lib/catalog/types'

export const metadata = {
  title: 'Rubros — Plataforma Cordillera',
}

/**
 * Los rubros del catálogo: cuánto se gastó en cada uno, cuántos productos tiene
 * y con cuántas formas llega escrito.
 *
 * Toda la pantalla es un solo panel, `RubroNormalizer`. No hay encabezado ni
 * accesos rápidos arriba: el panel ya se titula y lleva sus propias entradas a
 * las colas (sin rubro, equivalencias, revisión). Un H1 «Rubros» y una barra de
 * enlaces encima eran el resto de la pantalla vieja y decían dos veces lo mismo.
 *
 * **Los mantiene compras, y ventas los consulta** (010). No hay ningún rol
 * escrito acá: las acciones se ofrecen según lo que la matriz de permisos diga
 * de esta sección, que es el mismo lugar donde el backend decide el 403.
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
    <RubroNormalizer
      listing={listing}
      canEdit={canEdit(session?.permissions ?? {}, 'PRODUCT_CATEGORIES')}
    />
  )
}
