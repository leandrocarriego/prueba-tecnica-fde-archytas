/**
 * Reading the permission map the backend hands out.
 *
 * There is no matrix here on purpose. The rules live in `identity` and are
 * enforced on every request; what the browser gets is the answer for the
 * person asking, and this file only knows how to read it. Two copies of a rule
 * are one rule and one bug.
 */

import type { components } from '@/lib/api/types'

export type Section = components['schemas']['Section']
export type Permissions = Partial<Record<Section, number>>

/** The three levels, in the order the backend defines them. */
export const NONE = 0
export const READ = 1
export const WRITE = 2

/** Whether this person reaches a section at all. */
export function canSee(permissions: Permissions, section: Section): boolean {
  return (permissions[section] ?? NONE) >= READ
}

/**
 * Whether this person may change what is in it.
 *
 * Hiding a button is a convenience, never the restriction: the backend refuses
 * the change regardless. This exists so the screen does not offer somebody
 * something that will be refused.
 */
export function canEdit(permissions: Permissions, section: Section): boolean {
  return (permissions[section] ?? NONE) >= WRITE
}
