/**
 * Every load and correction somebody can make, in one list.
 *
 * RF-20 asks for a single screen that gathers them, and RF-21 that each person
 * sees only theirs. Both are answered here: an action declares the section and
 * level its route already demands, and the screen filters by the permission map
 * the backend hands out with the session.
 *
 * **This is a view, not a permission.** The refusal lives in the route — every
 * endpoint declares its own authorisation and `PY-09` has a test that says so —
 * and this list only decides what to offer. That is deliberate: the brief asks
 * for permissions "verificados en cada consulta y no sólo escondiendo opciones
 * del menú", and a list that could grant something would be a second place
 * where who-may-do-what is decided. The day the two disagreed, the route would
 * win and this list would simply be lying.
 *
 * Every feature adds its line here when it lands, the same way it adds its
 * parameter to the catalog. The first four are what 003 left; the rest arrived
 * with 004 to 009, and between them they are what makes this screen useful to
 * somebody who does not touch prices: whoever handles purchasing loads a
 * payment and issues a receipt, whoever handles sales classifies a product and
 * resolves a repeated sale.
 */
import { canEdit, canSee, type Permissions, type Section } from '@/lib/auth/permissions'

export interface ManualAction {
  /** Stable, for React keys and for tests that name one. */
  readonly id: string
  /** What it does, in the words the person would use. */
  readonly label: string
  /** When to use it. One sentence, so the screen is readable at a glance. */
  readonly description: string
  /** Where it is done. The action itself lives on that screen. */
  readonly href: string
  /** The section its route demands, and whether it demands the level to write. */
  readonly section: Section
  readonly writes: boolean
}

export const MANUAL_ACTIONS: readonly ManualAction[] = [
  {
    id: 'request-price-update',
    label: 'Pedir la lista de precios ahora',
    description: 'Le pide el listado al portal sin esperar a la próxima consulta automática.',
    href: '/precios',
    section: 'PRICES',
    writes: true,
  },
  {
    id: 'resolve-triage-case',
    label: 'Resolver un caso de la cola de revisión',
    description: 'Decidí qué hacer con lo que el sistema no pudo interpretar solo.',
    href: '/revision',
    section: 'PRICES',
    writes: true,
  },
  {
    id: 'correct-product',
    label: 'Corregir un precio o un producto',
    description: 'Cambiá a mano un dato que llegó mal, diciendo por qué. Se guarda lo que decía.',
    href: '/precios',
    section: 'PRODUCT_CATALOG',
    writes: true,
  },
  {
    id: 'revert-correction',
    label: 'Deshacer una corrección',
    description: 'Devolvé un dato al valor que había informado el portal.',
    href: '/precios',
    section: 'MANUAL_CORRECTIONS',
    writes: true,
  },
  {
    id: 'resolve-invoice-review',
    label: 'Resolver una factura apartada',
    description: 'Decí de qué proveedor es, o que la factura está bien como está.',
    href: '/facturas/revision',
    section: 'PURCHASE_INVOICES',
    writes: true,
  },
  {
    id: 'correct-supplier',
    label: 'Corregir los datos de un proveedor',
    description: 'Cambiá el correo, el teléfono o el plazo pactado. Se guarda lo que decía.',
    href: '/proveedores',
    section: 'SUPPLIERS',
    writes: true,
  },
  {
    id: 'register-payment',
    label: 'Registrar un pago a mano',
    description: 'Cargá un pago sobre una factura, con su monto y su fecha.',
    href: '/facturas',
    section: 'PAYMENTS',
    writes: true,
  },
  {
    id: 'issue-receipt',
    label: 'Emitir el recibo de recepción de una factura',
    description: 'Se puede hasta el día del vencimiento, y queda con tu nombre.',
    href: '/facturas',
    section: 'RECEIPTS',
    writes: true,
  },
  {
    id: 'add-due-date',
    label: 'Agregar o mover un vencimiento',
    description: 'Cargá algo que vence, o corré una fecha diciendo por qué.',
    href: '/calendario',
    section: 'CALENDAR',
    writes: true,
  },
  {
    id: 'dismiss-repeat-order',
    label: 'Descartar un aviso de pedido repetido',
    description: 'Si la orden no repite a otra, sacale el señalamiento.',
    href: '/ordenes',
    section: 'PURCHASE_ORDERS',
    writes: true,
  },
  {
    id: 'resolve-message',
    label: 'Resolver un mensaje de la bandeja',
    description: 'Marcá que ya lo atendiste, o dejá una nota sobre qué falta.',
    href: '/mensajes',
    section: 'SUPPLIER_MESSAGES',
    writes: true,
  },
  {
    id: 'classify-product',
    label: 'Darle su rubro a un producto',
    description: 'Confirmá la propuesta del sistema, o elegí otro rubro.',
    href: '/rubros/sin-clasificar',
    section: 'PRODUCT_CATEGORIES',
    writes: true,
  },
  {
    id: 'resolve-sale',
    label: 'Resolver una venta apartada',
    description: 'Decidí cuál versión de una venta repetida vale, o corregí un dato roto.',
    href: '/ventas/revision',
    section: 'SALES',
    writes: true,
  },
]

/** The actions this person may actually run, in the order they are declared. */
export function actionsFor(permissions: Permissions): ManualAction[] {
  return MANUAL_ACTIONS.filter(action =>
    action.writes ? canEdit(permissions, action.section) : canSee(permissions, action.section)
  )
}
