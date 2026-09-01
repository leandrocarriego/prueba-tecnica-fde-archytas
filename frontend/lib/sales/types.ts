/** Sales and dashboard types, derived from the generated OpenAPI schema (`TS-05`). */
import type { components } from '@/lib/api/types'

export type Sale = components['schemas']['SaleRead']
export type SaleList = components['schemas']['SaleList']
export type SaleGroup = components['schemas']['SaleGroup']
export type ReviewQueue = components['schemas']['ReviewQueue']
export type ResolvedGroup = components['schemas']['ResolvedGroup']
export type SalesDashboard = components['schemas']['SalesDashboard']
export type MonthTotal = components['schemas']['MonthTotal']
export type CatalogDashboard = components['schemas']['CatalogDashboard']
export type StockCut = components['schemas']['StockCut']
export type PriceCurvePoint = components['schemas']['PriceCurvePoint']
