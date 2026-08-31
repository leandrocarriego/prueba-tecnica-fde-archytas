import Link from 'next/link'

import { getSession } from '@/app/actions/auth'
import { AliasList } from '@/components/categories/AliasList'
import { NoPermission } from '@/components/common/NoPermission'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { CategoryAlias, CategoryList, Rule } from '@/lib/catalog/types'

export const metadata = {
  title: 'Equivalencias — Plataforma Cordillera',
}

/**
 * Qué forma escrita significa qué rubro, con quién lo decidió (H5).
 *
 * Las que vinieron con el sistema dicen que las decidió la puesta en marcha, y
 * no el dueño: una equivalencia sembrada no la decidió nadie, y atribuírsela a
 * alguien sería mentir en un registro de auditoría.
 */
export default async function AliasesPage() {
  const [aliases, categories, rules, session] = await Promise.all([
    fetchFromApi<CategoryAlias[]>('/categories/aliases'),
    fetchFromApi<CategoryList>('/categories'),
    fetchFromApi<Rule[]>('/triage/rules?kind=unknown_category'),
    getSession(),
  ])

  if (aliases === null || categories === null) {
    return <NoPermission what="los rubros del catálogo" />
  }

  return (
    <main className="mx-auto max-w-5xl space-y-8 p-8">
      <Link className="text-sm text-muted-foreground underline" href="/rubros">
        « Volver a los rubros
      </Link>

      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Equivalencias</h1>
        <p className="text-sm text-muted-foreground">
          {aliases.length} formas escritas asignadas a un rubro. El sistema las aplica solo.
        </p>
      </header>

      <AliasList
        aliases={aliases}
        categories={categories.items}
        rules={rules ?? []}
        canEdit={canEdit(session?.permissions ?? {}, 'PRODUCT_CATEGORIES')}
      />
    </main>
  )
}
