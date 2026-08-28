import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merge class names, resolving Tailwind conflicts.
 *
 * `clsx` flattens conditionals; `twMerge` makes the last utility win when two
 * of the same family collide, so `cn('p-2', 'p-4')` yields `p-4` instead of
 * both classes fighting in the stylesheet.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
