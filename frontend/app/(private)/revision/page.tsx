import { getSession } from '@/app/actions/auth'
import { CaseQueue } from '@/components/triage/CaseQueue'
import { ReviewHeader } from '@/components/triage/ReviewHeader'
import { SavedDecisions } from '@/components/triage/SavedDecisions'
import { Empty, ErrorState } from '@/components/ui/state'
import { fetchFromApi } from '@/lib/api/server'
import { canEdit } from '@/lib/auth/permissions'
import type { CategoryList } from '@/lib/catalog/types'
import type { SupplierList } from '@/lib/purchases/types'
import type { ResolvedGroup, ReviewQueue } from '@/lib/sales/types'
import type { CaseList, Rule } from '@/lib/triage/types'

export const metadata = {
  title: 'Para decidir — Plataforma Cordillera',
}

interface ReviewPageProps {
  searchParams: Promise<{ area?: string }>
}

/**
 * «Para decidir»: lo que la plataforma apartó, y las decisiones tomadas sobre
 * eso.
 *
 * This screen is the visible half of Artículo II: nothing is discarded, so
 * everything the pipeline could not resolve on its own ends up here with the
 * reason it could not — and what a person decides is kept, so the queue empties
 * instead of growing.
 *
 * Desde la 011 es **la** lista, y no la de precios. Cuatro orígenes más —el
 * padrón, los comprobantes, el buzón y las ventas— apartaban en silencio, y
 * ahora caen acá. Que sea una sola no es una comodidad: lo que hizo que nadie
 * mirara el buzón del portal no fue que fuera largo, fue que era otro lugar más
 * al que había que acordarse de entrar.
 *
 * **Y cada uno ve lo suyo** (RF-12). El recorte lo hace el backend contra las
 * áreas que el rol de quien mira alcanza; acá no hay una segunda copia de esa
 * regla, ni la puede haber: la pantalla dibuja lo que le llega.
 *
 * La forma es la del diseño firmado (guía visual `3d`): encabezado con el
 * estado de la cola y el filtro por área, la lista angosta a la izquierda y el
 * caso abierto a la derecha. Antes era una pila de tarjetas todas abiertas —el
 * contenido correcto en una forma que no era ninguna de las acordadas.
 */
export default async function ReviewPage({ searchParams }: ReviewPageProps) {
  const { area } = await searchParams
  const session = await getSession()

  /*
    Las reglas aprendidas son **de precios**, y sólo las pide quien alcanza esa
    sección. Antes esta página las pedía siempre, y con la ruta de los casos
    abierta eso pasa a ser un 403 para cualquiera que no llegue a `PRICES` — un
    403 que `rules ?? []` disfrazaría de lista vacía. Un error amortiguado por
    accidente no es un comportamiento: es uno que nadie testea. Ahora la
    pregunta no se hace, y el bloque no se dibuja.
  */
  const mayReadRules = session !== null && canEdit(session.permissions, 'PRICES')
  /*
    Lo mismo para las ventas apartadas, y por la misma razón. Desde ahora una
    venta repetida o rota es un caso más de esta cola, y resolverla necesita el
    registro entero —las versiones enfrentadas, o el dato que falta—, que vive
    detrás de `SALES` en escritura. Quien no la alcanza ve el caso igual, con su
    motivo: lo que no ve es la venta.
  */
  const mayResolveSales = session !== null && canEdit(session.permissions, 'SALES')
  const query = area ? `&section=${encodeURIComponent(area)}` : ''

  const [cases, rules, categories, suppliers, salesQueue, decidedSales] = await Promise.all([
    fetchFromApi<CaseList>(`/triage/cases?limit=100${query}`),
    mayReadRules ? fetchFromApi<Rule[]>('/triage/rules') : Promise.resolve(null),
    // Los rubros, para que un caso de forma escrita nueva se pueda resolver acá
    // mismo (RF-14 de 010). Los pide la pantalla y no el panel: `CaseDetail` es
    // de `triage` y no tiene por qué saber que existe un catálogo.
    fetchFromApi<CategoryList>('/categories'),
    /*
      El padrón, para poder cargar a mano la factura o la orden que el portal
      publicó rota. Lo pide la pantalla y no el panel, igual que los rubros.

      Quien no alcanza el padrón recibe `null` —el backend contesta 403— y la
      carga a mano no se ofrece. No es una puerta que se esconde: sin proveedor
      no hay factura que registrar, y ofrecer un formulario que termina en un
      403 sería peor que decir quién puede hacerlo.
    */
    fetchFromApi<SupplierList>('/suppliers'),
    mayResolveSales ? fetchFromApi<ReviewQueue>('/sales/review') : Promise.resolve(null),
    /*
      Y las que ya se decidieron, que es lo que hace revocable la decisión
      (RF-34, RF-35, RF-36 de 009). Vive acá desde que `/ventas` es un listado:
      deshacer una decisión devuelve la venta a esta cola, así que la palanca y
      su consecuencia están en la misma pantalla.
    */
    mayResolveSales
      ? fetchFromApi<ResolvedGroup[]>('/sales/resolved?limit=50')
      : Promise.resolve(null),
  ])
  // Asked here so a case can offer the second door when a load is refused by a
  // correction in force. It is not the permission that opens this screen —
  // cualquier sesión llega, y el backend recorta por área— sino la de cambiar
  // una corrección, que es `PRODUCT_CATALOG` en escritura. Esto sólo mantiene
  // fuera del panel un link que respondería 403.
  const mayCorrect = session !== null && canEdit(session.permissions, 'PRODUCT_CATALOG')

  if (cases === null) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Para decidir</h1>
        <ErrorState title="No pudimos traer los pendientes.">
          Probá de nuevo en un momento.
        </ErrorState>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <ReviewHeader
        pendingTotal={cases.pending_total}
        resolvedToday={cases.resolved_today}
        oldestAt={cases.oldest_at ?? null}
        sections={cases.sections}
        area={area}
      />

      {cases.items.length === 0 ? (
        <Empty title="Nada apartado.">
          Cuando el sistema no pueda resolver algo solo, va a aparecer acá con el motivo.
        </Empty>
      ) : (
        <CaseQueue
          items={cases.items}
          pendingTotal={cases.pending_total}
          mayCorrect={mayCorrect}
          categories={categories?.items ?? []}
          suppliers={suppliers?.items ?? []}
          salesQueue={salesQueue}
          mayResolveSales={mayResolveSales}
        />
      )}

      {/*
        Todo lo ya decidido, en un solo bloque: las reglas aprendidas y las
        ventas resueltas son la misma clase de cosa —una decisión tomada que se
        puede revocar— y estaban en dos secciones distintas al pie.

        Se dibuja si quien mira alcanza **alguna** de las dos mitades; adentro,
        cada una aparece sólo si la trajo su consulta, que es la que el backend
        recorta por permisos.
      */}
      {(mayReadRules || mayResolveSales) && (
        <SavedDecisions rules={rules ?? []} sales={decidedSales ?? []} />
      )}
    </div>
  )
}
