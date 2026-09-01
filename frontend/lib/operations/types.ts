/**
 * Operations types, derived from the generated OpenAPI schema.
 *
 * These are aliases rather than hand-written interfaces on purpose: the backend
 * is the single source of truth for the contract, and a rename there should
 * break the build here instead of drifting silently.
 */
import type { components } from '@/lib/api/types'

export type JobStatus = components['schemas']['JobStatus']
export type JobRun = components['schemas']['JobRunRead']
export type JobRunList = components['schemas']['JobRunList']

export type Parameter = components['schemas']['ParameterRead']
export type ParameterKind = components['schemas']['ParameterKind']
export type AuditEntry = components['schemas']['AuditEntryRead']
export type AuditEntryList = components['schemas']['AuditEntryList']
export type AuditAction = components['schemas']['AuditAction']
export type BusinessSection = components['schemas']['BusinessSection']
export type CorrectionReason = components['schemas']['CorrectionReasonRead']

/** Una de las seis cosas que la plataforma trae del portal, y en qué anda. */
export type SyncSource = components['schemas']['SyncSourceRead']
