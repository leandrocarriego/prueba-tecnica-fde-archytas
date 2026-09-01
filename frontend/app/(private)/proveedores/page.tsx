import Link from 'next/link'

import { Tile } from '@/components/common/Tile'
import { NoPermission } from '@/components/common/NoPermission'
import {
  SUPPLIER_VIEWS,
  SupplierFilters,
  type SupplierView,
} from '@/components/purchases/SupplierFilters'
import { SupplierTable } from '@/components/purchases/SupplierTable'
import { Money } from '@/components/ui/amount'
import { ErrorState } from '@/components/ui/state'
import { readFromApi } from '@/lib/api/server'
import { count } from '@/lib/format'
import type { Supplier, SupplierList } from '@/lib/purchases/types'

export const metadata = {
  title: 'Proveedores — Plataforma Cordillera',
}

interface SuppliersSearchParams {
  q?: string
  ver?: string
}

function viewFrom(value: string | undefined): SupplierView {
  return value !== undefined && value in SUPPLIER_VIEWS ? (value as SupplierView) : 'todos'
}

/** Si a este proveedor le falta algo que una persona tenga que completar. */
function needsReview(supplier: Supplier): boolean {
  return (supplier.missing ?? []).length > 0
}

/** Lo que se le debe, como número, para poder sumarlo y ordenarlo. */
function owed(supplier: Supplier): number {
  const value = Number(supplier.balance ?? 0)
  return Number.isNaN(value) ? 0 : value
}

/** Si el texto buscado aparece en el nombre, el CUIT o alguna grafía guardada. */
function matches(supplier: Supplier, needle: string): boolean {
  if (!needle) return true
  const haystack = [
    supplier.legal_name,
    supplier.tax_id ?? '',
    ...(supplier.aliases ?? []).map(alias => alias.text_original),
  ]
    .join(' ')
    .toLowerCase()
  return haystack.includes(needle)
}

/**
 * El índice de proveedores (H2 de 004), con la forma de la guía visual (`3n`).
 *
 * Encabezado con el estado del padrón, cuatro cuentas, y la tabla filtrable
 * ordenada por deuda — «ordenado por lo que importa», que es quién está
 * esperando plata y quién tiene un dato sin resolver.
 *
 * **No hay «Nuevo proveedor», y el diseño lo dibuja.** Es la única pieza de la
 * guía que no se puede construir: el padrón sale del portal y la plataforma no
 * da de alta a nadie por su cuenta (Artículo I). Un botón que abriera un
 * formulario de alta prometería una escritura contra un sistema que es de otro
 * y de sólo lectura. Tampoco hay «Exportar»: no existe todavía, y un botón que
 * no hace nada es peor que su ausencia.
 *
 * El filtrado ocurre acá y no en el backend porque `GET /suppliers` devuelve el
 * padrón entero —no pagina— así que la página ya tiene todas las filas: pedirlas
 * de nuevo para verlas recortadas sería un viaje por algo que está en memoria.
 */
export default async function SuppliersPage({
  searchParams,
}: {
  searchParams: Promise<SuppliersSearchParams>
}) {
  const { q, ver } = await searchParams
  const view = viewFrom(ver)
  const needle = (q ?? '').trim().toLowerCase()

  const read = await readFromApi<SupplierList>('/suppliers')
  if (!read.ok) {
    if (read.failure === 'unauthorized') {
      return <NoPermission what="el padrón de proveedores" />
    }
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Proveedores</h1>
        <ErrorState title="No pudimos traer el padrón.">Probá de nuevo en unos minutos.</ErrorState>
      </div>
    )
  }

  const all = read.data.items
  const toReview = all.filter(needsReview).length
  const withDebt = all.filter(supplier => owed(supplier) > 0)
  const debt = withDebt.reduce((total, supplier) => total + owed(supplier), 0)

  const shown = all
    .filter(supplier => matches(supplier, needle))
    .filter(supplier =>
      view === 'deuda' ? owed(supplier) > 0 : view === 'revisar' ? needsReview(supplier) : true
    )
    // Por deuda, de mayor a menor, y a igual deuda por nombre. El padrón se abre
    // para saber a quién hay que pagarle, así que ése es el orden de arriba.
    .sort((a, b) => owed(b) - owed(a) || a.legal_name.localeCompare(b.legal_name))

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-4 rounded-xl border border-border bg-card px-6 py-5">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Proveedores</h1>
          <p className="text-sm text-muted-foreground">
            {count(read.data.total)} en el padrón
            {toReview > 0 && ` · ${count(toReview)} con un dato sin completar`}. El padrón sale del
            portal: el sistema no da de alta ninguno por su cuenta.
          </p>
        </div>

        <Link
          className="inline-flex h-10 items-center rounded-md border border-input bg-card px-4 text-sm font-semibold text-foreground hover:bg-muted"
          href="/proveedores/grafias"
        >
          Grafías guardadas
        </Link>
      </header>

      <div className="flex flex-wrap gap-4">
        <Tile
          label="Deuda total"
          value={<Money value={String(debt)} as="span" />}
          sub={
            withDebt.length === 0
              ? 'No hay saldo abierto con ningún proveedor.'
              : `Repartida en ${count(withDebt.length)} ${
                  withDebt.length === 1 ? 'proveedor' : 'proveedores'
                }.`
          }
        />
        <Tile
          label="Con deuda abierta"
          value={count(withDebt.length)}
          sub={`De ${count(read.data.total)} en el padrón.`}
        />
        <Tile
          label="Facturas registradas"
          value={count(all.reduce((total, supplier) => total + supplier.invoice_count, 0))}
          sub="Todas las que el portal publicó, de todos los proveedores."
        />
        {/*
          La única con acento, y sólo cuando hay algo: un dato que falta es
          trabajo de una persona, y es la tarjeta que conecta este padrón con la
          bandeja de pendientes.
        */}
        <Tile
          label="Datos incompletos"
          value={count(toReview)}
          accent={toReview > 0}
          sub={
            toReview === 0 ? (
              'Ningún proveedor con datos faltantes.'
            ) : (
              <Link className="text-link hover:underline" href="/proveedores?ver=revisar">
                Completar →
              </Link>
            )
          }
        />
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <SupplierFilters q={q ?? ''} view={view} toReview={toReview} />
        <SupplierTable items={shown} />
      </div>

      <p className="text-xs text-muted-foreground">
        La columna de salud del dato es la que conecta este listado con la bandeja de pendientes: se
        entra al problema desde donde se lo ve.
      </p>
    </div>
  )
}
