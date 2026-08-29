/**
 * Price types, derived from the generated OpenAPI schema.
 *
 * Aliases rather than hand-written interfaces: the backend is the single source
 * of truth for the contract, and a rename there has to break the build here
 * instead of drifting silently (`TS-05`).
 */
import type { components } from '@/lib/api/types'

export type Price = components['schemas']['PriceRead']
export type PriceList = components['schemas']['PriceList']
export type PriceHistory = components['schemas']['PriceHistoryRead']
export type PricePoint = components['schemas']['PricePointRead']
export type PriceUpdateStatus = components['schemas']['PriceUpdateStatusRead']
export type PriceUpdateSettings = components['schemas']['PriceUpdateSettingsRead']
export type JobRun = components['schemas']['JobRunRead']
