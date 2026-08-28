# `lib/api/` — Cliente tipado del backend

`types.ts` está **generado** a partir del schema de OpenAPI del backend. No se edita a mano.

```bash
# el backend tiene que estar corriendo
npm run generate-api-types
```

Se versiona a propósito: así el frontend compila en un clon limpio sin necesidad de levantar
el backend primero. Hay que regenerarlo cada vez que cambia una ruta o un schema — si no, el
desfasaje aparece como un bug en producción en vez de como un error de tipos.

## Uso

Desde el navegador (pasa por el proxy, que inyecta el token de la cookie httpOnly):

```typescript
import { apiClient } from '@/lib/api/client'

const { data, error } = await apiClient.GET('/api/v1/operations/jobs', {
  params: { query: { limit: 20 } },
})
```

Desde un Server Component o una Server Action, con el token a mano:

```typescript
import { createServerClient } from '@/lib/api/client'

const client = createServerClient(token)
const { data } = await client.GET('/api/v1/users')
```

## Tipos del dominio

No escribas a mano un tipo que ya existe en el schema:

```typescript
import type { components } from '@/lib/api/types'

type JobRun = components['schemas']['JobRunRead']
type UserRole = components['schemas']['UserRole']
```
