/**
 * Job run types, derived from the generated OpenAPI schema.
 *
 * These are aliases rather than hand-written interfaces on purpose: the backend
 * is the single source of truth for the contract, and a rename there should
 * break the build here instead of drifting silently.
 */
import type { components } from '@/lib/api/types'

export type JobStatus = components['schemas']['JobStatus']
export type JobRun = components['schemas']['JobRunRead']
export type JobRunList = components['schemas']['JobRunList']
