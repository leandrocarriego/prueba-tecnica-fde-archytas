'use server'

import { revalidatePath } from 'next/cache'
import { cookies } from 'next/headers'

import type { ActionResult } from '@/app/actions/prices'
import type {
  AliasPreview,
  DueDate,
  Incident,
  Invoice,
  Payment,
  PurchaseOrder,
  Receipt,
  Supplier,
} from '@/lib/purchases/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_PREFIX = '/api/v1'

const UNREACHABLE = 'No se pudo contactar al servidor'
const NO_SESSION = 'La sesión expiró. Iniciá sesión de nuevo'

interface ApiErrorBody {
  error?: { type?: string; message?: string; details?: Record<string, unknown> }
}

/**
 * One call to the API, with the session the server already holds.
 *
 * The failure comes back as a value and never as an exception: every one of
 * these is answered by a form, and a form that has to catch is a form that
 * shows a stack trace to whoever is doing their job.
 */
async function call<T>(path: string, init: RequestInit): Promise<ActionResult<T>> {
  const token = (await cookies()).get('access_token')?.value
  if (!token) return { ok: false, message: NO_SESSION }

  try {
    const response = await fetch(`${API_URL}${API_PREFIX}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...(init.headers ?? {}),
      },
      cache: 'no-store',
    })

    if (response.status === 204) return { ok: true, data: undefined as T }

    const body = (await response.json()) as T & ApiErrorBody
    if (!response.ok) return { ok: false, message: body.error?.message ?? UNREACHABLE }
    return { ok: true, data: body }
  } catch {
    return { ok: false, message: UNREACHABLE }
  }
}

// --- Facturas y proveedores (004) ----------------------------------------

/** What a person corrected about a held invoice, when they corrected anything. */
export interface InvoiceCorrections {
  number?: string
  issued_on?: string
  total?: string
}

/**
 * Decide about an invoice held for review (RF-31, RF-32, RF-33 of 004).
 *
 * A field that goes empty is **not sent**: leaving it alone is how somebody
 * confirms what the table published, and sending it back unchanged would write
 * a correction into the log that nobody made.
 */
export async function resolveInvoice(
  invoiceId: number,
  supplierId: number | null,
  remember = true,
  corrections: InvoiceCorrections = {}
): Promise<ActionResult<Invoice>> {
  const body: Record<string, unknown> = { supplier_id: supplierId, remember }
  for (const [field, value] of Object.entries(corrections)) {
    if (value) body[field] = value
  }
  const result = await call<Invoice>(`/invoice-review/${invoiceId}/resolve`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
  if (result.ok) {
    revalidatePath('/facturas/revision')
    revalidatePath('/facturas')
    revalidatePath(`/facturas/${invoiceId}`)
  }
  return result
}

/**
 * How many held invoices an assignment would resolve, before it is saved.
 *
 * RF-48 of 004, and the reason it is a call and not a guess on the screen: the
 * number promised here is counted by the same query that then resolves them.
 */
export async function previewAlias(
  text: string,
  supplierId: number
): Promise<ActionResult<AliasPreview>> {
  return call<AliasPreview>('/supplier-aliases/preview', {
    method: 'POST',
    body: JSON.stringify({ text, supplier_id: supplierId }),
  })
}

/** Assign a spelling to a supplier, and resolve what was waiting on it (RF-47, RF-49). */
export async function saveAlias(
  text: string,
  supplierId: number
): Promise<ActionResult<AliasPreview>> {
  const result = await call<AliasPreview>('/supplier-aliases', {
    method: 'POST',
    body: JSON.stringify({ text, supplier_id: supplierId }),
  })
  if (result.ok) {
    revalidatePath('/proveedores/grafias')
    revalidatePath('/facturas/revision')
    revalidatePath('/facturas')
  }
  return result
}

/** Leave an assignment without effect. What it resolved goes back (RF-52, RF-53). */
export async function dropAlias(aliasId: number): Promise<ActionResult<void>> {
  const result = await call<void>(`/supplier-aliases/${aliasId}`, { method: 'DELETE' })
  if (result.ok) {
    revalidatePath('/proveedores/grafias')
    revalidatePath('/facturas/revision')
  }
  return result
}

/** Correct the contact details of a supplier (RF-16 to RF-19 of 004). */
export async function correctSupplier(
  supplierId: number,
  values: { email?: string | null; phone?: string | null; payment_term_days?: number | null },
  reasonCode: string,
  reasonDetail?: string
): Promise<ActionResult<Supplier>> {
  const result = await call<Supplier>(`/suppliers/${supplierId}`, {
    method: 'PATCH',
    body: JSON.stringify({ ...values, reason_code: reasonCode, reason_detail: reasonDetail }),
  })
  if (result.ok) revalidatePath(`/proveedores/${supplierId}`)
  return result
}

// --- Pagos y recibos (005) -----------------------------------------------

/**
 * Register a payment by hand (RF-18 of 005).
 *
 * A payment over the outstanding balance comes back refused the first time,
 * with the balance in the message: that **is** the warning of RF-21, and it is
 * answered by sending it again with `confirmOverBalance`.
 */
export async function registerPayment(
  invoiceId: number,
  amount: string,
  paidOn: string,
  reference: string | null,
  confirmOverBalance = false
): Promise<ActionResult<Payment>> {
  const result = await call<Payment>(`/invoices/${invoiceId}/payments`, {
    method: 'POST',
    body: JSON.stringify({
      amount,
      paid_on: paidOn,
      reference,
      confirm_over_balance: confirmOverBalance,
    }),
  })
  if (result.ok) {
    revalidatePath(`/facturas/${invoiceId}`)
    revalidatePath('/facturas')
  }
  return result
}

/** Leave a payment loaded by hand without effect (RF-22 of 005). */
export async function voidPayment(
  paymentId: number,
  invoiceId: number
): Promise<ActionResult<Payment>> {
  const result = await call<Payment>(`/payments/${paymentId}`, { method: 'DELETE' })
  if (result.ok) revalidatePath(`/facturas/${invoiceId}`)
  return result
}

/** Distribute a held voucher between the invoices it covers (RF-53 of 005). */
export async function splitPayment(
  paymentId: number,
  parts: Array<{ invoice_id: number; amount: string }>
): Promise<ActionResult<Payment[]>> {
  const result = await call<Payment[]>(`/payments/${paymentId}/split`, {
    method: 'POST',
    body: JSON.stringify({ parts }),
  })
  if (result.ok) revalidatePath('/facturas/pagos')
  return result
}

/** Issue the reception receipt of an invoice (RF-33 of 005). */
export async function issueReceipt(invoiceId: number): Promise<ActionResult<Receipt>> {
  const result = await call<Receipt>(`/invoices/${invoiceId}/receipt`, { method: 'POST' })
  if (result.ok) {
    revalidatePath(`/facturas/${invoiceId}`)
    revalidatePath('/calendario')
  }
  return result
}

/** Annul a receipt already issued (RF-49 of 005). */
export async function voidReceipt(
  receiptId: number,
  invoiceId: number
): Promise<ActionResult<Receipt>> {
  const result = await call<Receipt>(`/receipts/${receiptId}`, { method: 'DELETE' })
  if (result.ok) {
    revalidatePath(`/facturas/${invoiceId}`)
    revalidatePath('/calendario')
  }
  return result
}

/** Close the incident of an invoice that fell due without its receipt (RF-57). */
export async function closeIncident(
  incidentId: number,
  resolution: string
): Promise<ActionResult<Incident>> {
  const result = await call<Incident>(`/receipt-incidents/${incidentId}/close`, {
    method: 'POST',
    body: JSON.stringify({ resolution }),
  })
  if (result.ok) revalidatePath('/facturas/incidentes')
  return result
}

// --- El calendario (006) -------------------------------------------------

/** Add a due date by hand (RF-12 of 006). */
export async function addDueDate(
  onDate: string,
  description: string,
  amount: string | null
): Promise<ActionResult<DueDate>> {
  const result = await call<DueDate>('/calendar', {
    method: 'POST',
    body: JSON.stringify({ on_date: onDate, description, amount }),
  })
  if (result.ok) revalidatePath('/calendario')
  return result
}

/** Correct a hand-made entry (RF-15 of 006). */
export async function editDueDate(
  dueDateId: number,
  description: string | null,
  amount: string | null
): Promise<ActionResult<DueDate>> {
  const result = await call<DueDate>(`/calendar/${dueDateId}`, {
    method: 'PATCH',
    body: JSON.stringify({ description, amount }),
  })
  if (result.ok) revalidatePath('/calendario')
  return result
}

/**
 * Move an entry to another day (RF-19, RF-22, RF-25, RF-42 of 006).
 *
 * Dragging it and picking a date are this same call: how the person says it is
 * the browser's business, and the platform has no reason to tell them apart.
 * A date already past is refused once and accepted on the second try, which is
 * what "pedir confirmación" means over HTTP.
 */
export async function moveDueDate(
  dueDateId: number,
  onDate: string,
  reason: string | null,
  confirmPast = false
): Promise<ActionResult<DueDate>> {
  const result = await call<DueDate>(`/calendar/${dueDateId}/date`, {
    method: 'PUT',
    body: JSON.stringify({ on_date: onDate, reason, confirm_past: confirmPast }),
  })
  if (result.ok) revalidatePath('/calendario')
  return result
}

/** Remove a hand-made entry (RF-17 of 006). One from an invoice is refused (RF-18). */
export async function removeDueDate(dueDateId: number): Promise<ActionResult<void>> {
  const result = await call<void>(`/calendar/${dueDateId}`, { method: 'DELETE' })
  if (result.ok) revalidatePath('/calendario')
  return result
}

// --- Las órdenes de compra (007) -----------------------------------------

/** Drop the repeated-order flag, recording who did it (RF-18, RF-19 of 007). */
/**
 * Decir de qué proveedor del padrón es una orden apartada (RF-54, RF-61 de 007).
 *
 * `remember` va en `true` y es lo que convierte la decisión en criterio: la
 * misma forma de escribir el nombre no se vuelve a preguntar, y **las otras
 * órdenes y facturas que estaban esperando esa grafía quedan resueltas con
 * ésta** (RF-62). El relevamiento midió veinte formas distintas de escribir un
 * nombre sólo en las órdenes.
 */
export async function resolveOrder(
  orderId: number,
  supplierId: number
): Promise<ActionResult<PurchaseOrder>> {
  const result = await call<PurchaseOrder>(`/purchase-orders/${orderId}/resolution`, {
    method: 'POST',
    body: JSON.stringify({ supplier_id: supplierId, remember: true }),
  })
  if (result.ok) {
    revalidatePath('/ordenes')
  }
  return result
}

export async function dismissRepeat(orderId: number): Promise<ActionResult<PurchaseOrder>> {
  const result = await call<PurchaseOrder>(`/purchase-orders/${orderId}/repeat-flag`, {
    method: 'DELETE',
  })
  if (result.ok) revalidatePath('/ordenes')
  return result
}

/**
 * Decir que esta persona tiene el calendario abierto (H5 de 006).
 *
 * Se llama cada tanto mientras la pantalla está a la vista. No revalida nada ni
 * devuelve nada útil: lo único que hace es que los demás navegadores se enteren
 * de que hay alguien más mirando, por el mismo canal por el que ya viajan los
 * cambios.
 *
 * Un fallo se traga a propósito. Que no se pueda anunciar la presencia no puede
 * romper el calendario: la pantalla sigue andando y lo único que se pierde es
 * saber quién más está del otro lado.
 */
export async function announceCalendarPresence(): Promise<void> {
  await call<void>('/calendar/presence', { method: 'POST' })
}
