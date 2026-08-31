/**
 * Purchases types, derived from the generated OpenAPI schema.
 *
 * Aliases rather than hand-written interfaces: the backend is the single source
 * of truth for the contract, and a rename there has to break the build here
 * instead of drifting silently (`TS-05`).
 */
import type { components } from '@/lib/api/types'

export type Invoice = components['schemas']['InvoiceRead']
export type InvoiceList = components['schemas']['InvoiceList']
export type InvoiceDocument = components['schemas']['InvoiceDocumentRead']
export type Supplier = components['schemas']['SupplierRead']
export type SupplierList = components['schemas']['SupplierList']
export type SupplierAlias = components['schemas']['SupplierAliasRead']
export type SupplierCorrectionMark = components['schemas']['SupplierCorrectionMark']
export type SupplierTotals = components['schemas']['SupplierTotalsRead']
export type AgingBucket = components['schemas']['AgingBucket']
export type Payment = components['schemas']['PaymentRead']
export type Receipt = components['schemas']['ReceiptRead']
export type Incident = components['schemas']['IncidentRead']
export type Calendar = components['schemas']['CalendarRead']
export type DueDate = components['schemas']['DueDateRead']
export type DueDateChange = components['schemas']['DueDateChangeRead']
export type PurchaseOrder = components['schemas']['PurchaseOrderRead']
export type PurchaseOrderList = components['schemas']['PurchaseOrderList']
export type AliasPreview = components['schemas']['AliasPreview']
