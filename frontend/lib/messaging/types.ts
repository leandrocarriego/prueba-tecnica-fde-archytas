/** Inbox types, derived from the generated OpenAPI schema (`TS-05`). */
import type { components } from '@/lib/api/types'

export type Message = components['schemas']['MessageRead']
export type MessageList = components['schemas']['MessageList']
export type MessageKind = components['schemas']['MessageKind']
export type MessageState = components['schemas']['MessageState']
