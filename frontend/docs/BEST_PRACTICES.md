# Buenas prácticas del frontend — Plataforma Cordillera

Guía práctica para escribir el frontend de la plataforma. El _dónde vive cada cosa_ está en
[`ARCHITECTURE.md`](./ARCHITECTURE.md); acá está el _cómo se escribe_.

Los ejemplos usan el dominio real del producto: corridas de extracción (`operations`), cola de
excepciones (`triage`), proveedores (`suppliers`). El código va en **inglés**; los textos que ve
el usuario, en **español**.

## Índice

- [Organización del código](#organización-del-código)
- [Server Components por defecto](#server-components-por-defecto)
- [Tipos generados desde OpenAPI](#tipos-generados-desde-openapi)
- [Acceso al backend](#acceso-al-backend)
- [Patrones de componentes](#patrones-de-componentes)
- [Estado](#estado)
- [Carga, error y vacío](#carga-error-y-vacío)
- [Rendimiento](#rendimiento)
- [Seguridad](#seguridad)
- [Antipatrones](#antipatrones)
- [Calidad y checklist de review](#calidad-y-checklist-de-review)

## Organización del código

### Dónde va cada cosa

| Qué                                        | Dónde                             |
| ------------------------------------------ | --------------------------------- |
| Página de un módulo                        | `app/(private)/<modulo>/page.tsx` |
| Componentes de un módulo                   | `components/<modulo>/`            |
| Primitivas de UI (shadcn/ui)               | `components/ui/`                  |
| Componentes genéricos sin dominio          | `components/common/`              |
| Tipos, hooks y acceso a datos de un módulo | `lib/<modulo>/`                   |
| Hooks transversales                        | `lib/hooks/`                      |
| Mutaciones (Server Actions)                | `app/actions/<modulo>.ts`         |
| Sesión y proxy hacia el backend            | `app/api/`                        |

Los módulos del frontend siguen a los del backend: `auth`, `operations`, `triage`, `suppliers`,
`catalog`, `purchasing`, `billing`, `sales`. **No hay división `core/` vs `custom/`** en ningún
directorio: es un producto único, organizado por módulo de dominio igual que el backend.

Un hook propio de un módulo va junto a sus tipos y helpers en `lib/<modulo>/`; si es puramente de
presentación puede vivir en `components/<modulo>/hooks/`. Sólo lo que usan varios módulos va a
`lib/hooks/`.

### Nombres de archivos

```
✅ Bien:
- JobRunTable.tsx        componente → PascalCase
- JobRunCard.tsx     componente
- useJobRuns.ts          hook → camelCase con prefijo use, sin JSX → .ts
- taskStateUtils.ts      utilidad
- jobs.ts                acceso a datos del módulo
- types.ts               tipos propios de la vista
- button.tsx             primitiva de shadcn/ui → mantiene kebab-case

❌ Mal:
- job-run-table.tsx      componente en kebab-case
- useJobRuns.tsx         hook sin JSX con extensión .tsx
- JobRunService.ts       archivo en PascalCase que no exporta un componente
- utils.ts               dentro de un módulo: demasiado genérico
```

### Orden de imports

```typescript
// 1. React y Next.js
import { useState } from 'react'
import Image from 'next/image'

// 2. Librerías de terceros
import { toast } from 'sonner'

// 3. Primitivas de UI
import { Card } from '@/components/ui/card'

// 4. Componentes de módulo
import { JobRunCard } from '@/components/operations/JobRunCard'

// 5. Hooks
import { useJobRuns } from '@/lib/operations/useJobRuns'

// 6. Acceso a datos
import { fetchJobRuns } from '@/lib/operations/jobs'

// 7. Utilidades
import { getTaskStateLabel } from '@/lib/operations/taskStateUtils'

// 8. Tipos
import type { JobRun } from '@/lib/operations/types'

// 9. Relativos
import './styles.css'
```

## Server Components por defecto

Todo componente es Server Component hasta que se demuestre lo contrario. `'use client'` se
justifica sólo con: interactividad con estado, hooks de React, o APIs del navegador.

El patrón que se repite: **la página resuelve los datos en el servidor y baja al cliente sólo la
isla que necesita interactuar.**

```typescript
// app/(private)/operations/page.tsx — Server Component (sin 'use client')
import { JobRunTable } from '@/components/operations/JobRunTable'
import { listJobRuns } from '@/lib/operations/jobs.server'

export default async function OperationsPage() {
  const page = await listJobRuns({ limit: 20 })

  return (
    <main className="space-y-4 p-6">
      <h1 className="text-2xl font-semibold">Corridas de extracción</h1>
      <JobRunTable initialRuns={page.items} />
    </main>
  )
}
```

```typescript
// components/operations/JobRunTable.tsx — isla cliente: tiene botón de refrescar
'use client'

import { Button } from '@/components/ui/button'
import { useJobRuns } from '@/lib/operations/useJobRuns'
import { getTaskStateLabel, getTaskStateColor } from '@/lib/operations/taskStateUtils'
import type { JobRun } from '@/lib/operations/types'

interface JobRunTableProps {
  initialRuns: JobRun[]
}

export function JobRunTable({ initialRuns }: JobRunTableProps) {
  const { runs, isLoading, error, refresh } = useJobRuns(initialRuns)

  return (
    <section>
      <Button onClick={refresh} disabled={isLoading}>
        {isLoading ? 'Actualizando…' : 'Actualizar'}
      </Button>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {runs.length === 0 ? (
        <p className="text-muted-foreground">Todavía no hay corridas registradas.</p>
      ) : (
        <ul>
          {runs.map(run => (
            <li key={run.id}>
              <span>{run.task_name}</span>
              <span className={getTaskStateColor(run.status)}>
                {getTaskStateLabel(run.status)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
```

Nota sobre el ejemplo: `taskStateUtils` traduce hoy los estados de Celery
(`PENDING`/`STARTED`/`RETRY`/`SUCCESS`/`FAILURE`), que todavía no son los mismos que expone
`GET /api/v1/operations/jobs` (`PENDING`/`RUNNING`/`SUCCEEDED`/`FAILED`). Hasta que se unifiquen,
un estado que el mapa no conoce se muestra tal cual.

Errores frecuentes:

- Marcar la página entera con `'use client'` porque un botón adentro necesita estado. Se extrae
  el botón a su propio componente cliente.
- Traer datos con `useEffect` cuando el Server Component ya podía resolverlos.
- Poner `'use client'` en un archivo que sólo exporta tipos o helpers puros.

## Tipos generados desde OpenAPI

El contrato con el backend **se genera, no se escribe a mano**:

```bash
npm run generate-api-types   # backend levantado → lib/api/types.ts
```

`lib/api/types.ts` está generado: **no se edita a mano**, se regenera. Sí se versiona, para que
un clon limpio compile sin necesidad de levantar el backend primero — pero hay que regenerarlo
cada vez que cambia una ruta o un schema, o el desfasaje aparece en producción en vez de como
un error de tipos.

```typescript
// lib/operations/types.ts
import type { components } from '@/lib/api/types'

// ✅ El contrato viene del schema de OpenAPI del backend
export type JobRun = components['schemas']['JobRunRead']
export type JobRunPage = components['schemas']['JobRunList']
export type JobStatus = components['schemas']['JobStatus']

// ✅ Sólo se escribe a mano lo que es propio de la vista y no existe en la API
export interface JobRunFilters {
  taskName?: string
  status?: JobStatus
}
```

```typescript
// ❌ Mal: duplicar a mano un contrato que el backend ya publica
export interface JobRun {
  id: number
  task_name: string
  status: string // se desincroniza en cuanto el backend agrega un estado
}
```

Cuando los tipos no coinciden con lo que devuelve la API, la respuesta es regenerarlos, nunca
"ajustarlos" a mano ni tapar el error con `as`.

## Acceso al backend

Hay dos caminos, los dos del lado del servidor. **El token nunca toca el JavaScript del
navegador.**

### 1. Desde el servidor (Server Components, Server Actions, route handlers)

Se llama directo a `${NEXT_PUBLIC_API_URL}/api/v1/...` leyendo la cookie httpOnly:

```typescript
// lib/operations/jobs.server.ts
import { cookies } from 'next/headers'
import type { JobRunPage } from '@/lib/operations/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function listJobRuns({ limit = 20 }: { limit?: number }): Promise<JobRunPage> {
  const token = (await cookies()).get('access_token')?.value

  const response = await fetch(`${API_URL}/api/v1/operations/jobs?limit=${limit}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  })

  if (!response.ok) {
    throw new Error('No se pudieron obtener las corridas de extracción.')
  }

  return response.json()
}
```

### 2. Desde el cliente: siempre por el proxy

`app/api/proxy/[...path]/route.ts` es un route handler que:

1. lee el `access_token` de la cookie httpOnly (si no está, responde `401`);
2. antepone `api/v1/` a la ruta pedida si todavía no la trae;
3. agrega el header `Authorization: Bearer <token>` y reenvía a `NEXT_PUBLIC_API_URL`,
   conservando la query string;
4. devuelve el JSON del backend con su mismo status.

Es decir: `fetch('/api/proxy/operations/jobs')` → `GET ${NEXT_PUBLIC_API_URL}/api/v1/operations/jobs`
con el token inyectado.

Por eso el proxy es un route handler y **no** un `rewrite` de `next.config.js`: un rewrite no
puede leer una cookie httpOnly ni inyectar el header.

```typescript
// lib/operations/jobs.ts — lecturas desde el cliente
import type { JobRunPage } from '@/lib/operations/types'

export async function fetchJobRuns(limit = 20): Promise<JobRunPage> {
  const response = await fetch(`/api/proxy/operations/jobs?limit=${limit}`, {
    cache: 'no-store',
  })

  if (!response.ok) {
    throw new Error('No se pudieron obtener las corridas de extracción.')
  }

  return response.json()
}
```

```typescript
// ❌ Mal: URL absoluta del backend desde el cliente.
// No lleva el token (la cookie es httpOnly) y expone la dirección interna de la API.
await fetch('http://localhost:8000/api/v1/operations/jobs')
```

### Endpoints disponibles hoy

`/api/v1/auth/*` · `/api/v1/users` · `/api/v1/health` · `/api/v1/operations/jobs` ·
`/api/v1/operations/parameters`

El resto de los módulos (`triage`, `suppliers`, `catalog`, `purchasing`, `billing`, `sales`)
todavía no tiene superficie HTTP. Si una vista la necesita, primero se especifica y se implementa
el endpoint en el backend: no se inventa una ruta en el frontend ni se mockea la respuesta dentro
del componente.

### Reglas de la capa de datos

- El `fetch` vive en `lib/<modulo>/`, nunca dentro del componente.
- Las mutaciones van por Server Action en `app/actions/<modulo>.ts`, no por `fetch` desde el cliente.
- La URL del backend sale de `NEXT_PUBLIC_API_URL`; nunca se hardcodea.
- Una lectura que necesita datos frescos usa `cache: 'no-store'`.

## Patrones de componentes

### Un componente, una responsabilidad

```typescript
// ✅ Bien: sólo muestra el estado de una corrida
export function JobRunCard({ status }: JobRunCardProps) {
  return <Card>…</Card>
}

// ❌ Mal: fetch + estado + polling + filtros + render, todo junto
export function OperationsManager() { … }
```

### La lógica va a un hook

```typescript
// ✅ Bien: la lógica separada de la UI
export function JobRunTable({ initialRuns }: JobRunTableProps) {
  const { runs, isLoading, error, refresh } = useJobRuns(initialRuns)
  return <section>…</section>
}

// ❌ Mal: 50 líneas de useState/useEffect adentro del componente
export function JobRunTable() {
  const [runs, setRuns] = useState<JobRun[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { /* fetch, reintentos, cancelación… */ }, [])
  return <section>…</section>
}
```

Las reglas de negocio no viven en el frontend: viven en el backend. En `lib/` sólo va lógica de
presentación (formato, etiquetas, colores, orden de una tabla).

### TypeScript estricto

```typescript
// ✅ Bien: props explícitas
interface JobRunCardProps {
  status: JobRun
  onRetry?: () => void
}

export function JobRunCard({ status, onRetry }: JobRunCardProps) { … }

// ❌ Mal
export function JobRunCard({ status, onRetry }: any) { … }
```

### Desestructurar props

```typescript
// ✅ Bien
export function Button({ children, onClick, disabled }: ButtonProps) { … }

// ❌ Mal
export function Button(props: ButtonProps) {
  return <button onClick={props.onClick}>{props.children}</button>
}
```

## Estado

### El estado de UI se queda local

```typescript
// ✅ Bien
export function SupplierSearch() {
  const [query, setQuery] = useState('')
  …
}

// ❌ Mal: subir el estado sin necesidad
export function SupplierSearch({ query, setQuery }: Props) { … }
```

### Un hook de módulo, completo

```typescript
// lib/operations/useJobRuns.ts
'use client'

import { useCallback, useState } from 'react'
import { fetchJobRuns } from '@/lib/operations/jobs'
import type { JobRun } from '@/lib/operations/types'

export function useJobRuns(initialRuns: JobRun[]) {
  const [runs, setRuns] = useState(initialRuns)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const page = await fetchJobRuns()
      setRuns(page.items)
    } catch {
      setError('No se pudieron actualizar las corridas. Intentá nuevamente.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  return { runs, isLoading, error, refresh }
}
```

### Antes de agregar estado, preguntarse si hace falta

Muchos "estados" del cliente son datos que el Server Component ya podía resolver. Un filtro que
se puede expresar como query param (`/operations?status=FAILED`) casi siempre es mejor en la URL
que en `useState`: es compartible, sobrevive al refresh y no necesita cliente.

### Evitar el prop drilling

```typescript
// ✅ Bien: composición o contexto
<AuthBrandingProvider>
  <Layout />
</AuthBrandingProvider>

// ❌ Mal: pasar user y theme por tres niveles hasta la hoja
<Routes user={user} theme={theme} />
```

## Carga, error y vacío

Toda vista que trae datos contempla los tres estados. El vacío **no** es un error.

```typescript
// ✅ Bien
if (isLoading) return <TableSkeleton />
if (error) return <ErrorMessage message={error} />
if (runs.length === 0) return <p>Todavía no hay corridas registradas.</p>
return <JobRunList runs={runs} />

// ❌ Mal: sólo el camino feliz
return <JobRunList runs={runs} />
```

En páginas, el estado de carga y el de error pueden ir en `loading.tsx` y `error.tsx` junto a
`page.tsx`.

### Los mensajes de error se escriben para una persona

```typescript
// ✅ Bien: en español, accionable, sin detalles técnicos
catch (error) {
  setError('No se pudo conectar con el servidor. Verificá tu conexión e intentá nuevamente.')
}

// ❌ Mal: se le muestra al usuario la excepción tal cual
catch (error) {
  setError(String(error)) // "TypeError: Cannot read property 'items' of undefined"
}
```

El detalle técnico va al log del servidor; el usuario recibe qué pasó y qué puede hacer. Y nunca
se traga la excepción en silencio: o se muestra, o se loguea, o las dos cosas.

## Rendimiento

### Memoización, con moderación

```typescript
// ✅ Bien: un cálculo realmente caro
const grouped = useMemo(() => groupRunsByTask(runs), [runs])

// ❌ Mal: optimización prematura
const id = useMemo(() => run.id, [run])
```

### Code splitting

```typescript
// ✅ Bien: componentes pesados y poco usados, bajo demanda
const ExceptionDiffViewer = dynamic(() => import('./ExceptionDiffViewer'), {
  loading: () => <Skeleton className="h-64" />,
  ssr: false,
})
```

### Imágenes

```typescript
// ✅ Bien
import Image from 'next/image'

<Image src="/logo.svg" alt="Cordillera" width={160} height={40} priority />

// ❌ Mal
<img src="/logo.svg" alt="Cordillera" />
```

## Seguridad

### La sesión es una cookie httpOnly

El `access_token` no es legible desde JavaScript, y así tiene que seguir. Nunca se copia a
`localStorage`, ni a un estado de React, ni a la URL. Si un componente cliente necesita datos
autenticados, la respuesta es el proxy, no exponer el token.

### Ocultar un elemento en la UI **no** es autorización

Los roles son `OWNER`, `PURCHASING` y `SALES`. La UI los usa para no mostrar acciones que el
usuario no puede ejecutar — eso es ergonomía, no seguridad. **El permiso lo enforcea el backend
en el endpoint**; la UI sólo lo refleja.

```typescript
// ✅ Bien: la UI refleja el permiso, el backend lo hace cumplir.
// GET /api/v1/operations/parameters ya responde 403 a quien no es OWNER.
{user.role === 'OWNER' && <ParametersLink />}

// ❌ Mal: creer que esconder el link alcanza.
// Sin el chequeo del backend, entrar a /operations/parameters a mano funciona igual.
```

Corolario: una página nueva no está protegida por no estar en el menú. La protección es
`app/(private)/` (sesión) más el rol exigido por el endpoint.

### No confiar en la validación del cliente

La validación en el formulario existe para dar feedback rápido, no para garantizar nada. El
backend valida siempre, de nuevo, con sus propios schemas.

### Sanitizar el contenido del usuario

```typescript
// ✅ Bien: React escapa por defecto
<div>{exception.rawValue}</div>

// ❌ Mal: dato del portal legacy inyectado como HTML
<div dangerouslySetInnerHTML={{ __html: exception.rawValue }} />
```

Vale especialmente para lo que viene de SIGProv: es contenido externo, no confiable.

### Variables de entorno

```typescript
// ✅ Sólo lo que puede ser público lleva el prefijo NEXT_PUBLIC_
const apiUrl = process.env.NEXT_PUBLIC_API_URL

// ✅ Los secretos se leen sólo del lado del servidor (route handlers, Server Actions)
const secret = process.env.SESSION_SECRET

// ❌ Un secreto con prefijo NEXT_PUBLIC_ queda en el bundle del navegador
const apiKey = process.env.NEXT_PUBLIC_API_KEY
```

Todo lo que lleva `NEXT_PUBLIC_` termina en el navegador: si no puede ser público, no lleva el
prefijo.

## Antipatrones

### `any`

```typescript
// ❌ Mal
function readValue(data: any) {
  return data.value
}

// ✅ Bien: unknown y un narrowing explícito, o el tipo generado
function readValue(data: unknown): string {
  if (typeof data === 'object' && data !== null && 'value' in data) {
    return String(data.value)
  }
  throw new Error('Respuesta inesperada del servidor.')
}
```

### Silenciar TypeScript

```typescript
// ❌ Mal
// @ts-ignore
const runs = response.items

// ✅ Bien: regenerar los tipos o corregir el contrato
const page: JobRunPage = await response.json()
```

## Calidad y checklist de review

```bash
npm run type-check     # tsc --noEmit
npm run lint           # ESLint (next/core-web-vitals)
npm run format:check   # Prettier
npm run build          # el build también valida los tipos
```

Todavía no hay runner de tests en el frontend: los gates automáticos de hoy son esos cuatro
comandos. Cuando se agregue uno, se documenta acá.

Antes de pedir review:

- [ ] Los componentes son chicos y tienen una sola responsabilidad
- [ ] La lógica está en hooks (`lib/<modulo>/`), no adentro del componente
- [ ] Los Server Components son el caso por defecto y cada `'use client'` tiene motivo
- [ ] Los tipos de la API salen de `npm run generate-api-types`, no están escritos a mano
- [ ] No hay `any` ni `@ts-ignore`
- [ ] Las llamadas del cliente van por `/api/proxy/...`; ninguna URL del backend hardcodeada
- [ ] Los estados de carga, error y vacío están cubiertos
- [ ] Los textos visibles están en español y los mensajes de error son accionables
- [ ] La visibilidad por rol acompaña a un permiso que el backend efectivamente enforcea
- [ ] `type-check`, `lint` y `format:check` pasan

## Referencias

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — estructura del frontend, rutas y flujo de sesión
- [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) — arquitectura del sistema completo
- [`../../agents/skills/add_frontend_feature.md`](../../agents/skills/add_frontend_feature.md) — procedimiento para agregar una feature
- [React](https://react.dev/learn) · [Next.js](https://nextjs.org/docs) · [TypeScript](https://www.typescriptlang.org/docs/)
