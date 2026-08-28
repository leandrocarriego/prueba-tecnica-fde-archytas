# Skill — Agregar una feature de frontend

Tags: [frontend] [feature] [nextjs]

## Objetivo
Implementar una feature de frontend siguiendo la estructura por módulo de dominio:
- las páginas viven en `frontend/app/(private)/<modulo>/`
- los componentes viven en `frontend/components/<modulo>/`
- las primitivas de UI (shadcn/ui) viven en `frontend/components/ui/`
- el acceso a la API vive en `frontend/lib/`
- usa Server Components por defecto y las convenciones del App Router

## Cuándo usarla
- Agregar una página o una capacidad nueva de UI.
- Extender la interfaz de un módulo de dominio existente.

## Precondiciones
- Existe una `spec.md` aprobada para la feature y los requisitos de UI están claros.
- El nombre del módulo está acordado: `kebab-case` para rutas, `PascalCase` para componentes.
- Los endpoints del backend que la feature consume ya existen (o están especificados en
  `contracts/`).

## Reglas (ESTRICTO)
- Modo estricto de TypeScript; sin tipos `any` (usar `unknown` si hace falta).
- Server Components por defecto; `'use client'` sólo con justificación.
- Los tipos de la API se **generan** desde el schema de OpenAPI, no se escriben a mano.
- Los strings que ve el usuario van en **español**; el código, en inglés.

## Pasos (ORDEN OBLIGATORIO)

### 1) Crear la carpeta de componentes del módulo
Crear `frontend/components/<modulo>/` con:
- los componentes de la feature (`.tsx`)
- `types.ts` si hacen falta tipos propios de la vista
- `hooks/` si hacen falta hooks propios

Las primitivas reutilizables (button, dialog, table, …) **no** se duplican acá: viven en
`frontend/components/ui/` y se agregan con el CLI de shadcn/ui.

### 2) Crear la página
Crear `frontend/app/(private)/<modulo>/page.tsx`.
- Server Component por defecto.
- Agregar `loading.tsx` y `error.tsx` cuando la carga o el error tengan que ser visibles.
- El chequeo de autenticación ya lo hace `app/(private)/layout.tsx`: no se repite por página.

### 3) Definir los tipos
- Generar los tipos de la API: `npm run generate-api-types`.
- Usar esos tipos como fuente de verdad del contrato con el backend.
- Definir en `types.ts` sólo lo que es propio de la vista y no existe en la API.

### 4) Implementar los componentes
- Empezar por Server Components.
- Usar `'use client'` únicamente para:
  - elementos interactivos (formularios, botones con estado)
  - APIs del navegador (`localStorage`, etc.)
  - hooks de React (`useState`, `useEffect`, …)
- Seguir los patrones de shadcn/ui y las utilidades de Tailwind del proyecto.

### 5) Conectar con el backend
- El cliente de API y los helpers de fetch viven en `frontend/lib/`.
- Mutaciones → Server Actions en `frontend/app/actions/`.
- Proxy o lógica de sesión → route handlers en `frontend/app/api/`.
- Nunca llamar al backend con URLs hardcodeadas: usar la configuración de `frontend/lib/`.

### 6) Manejar estados de carga y error
- Estado de carga visible (skeleton o `loading.tsx`).
- Estado de error con mensaje útil **en español**.
- Estado vacío contemplado (lista sin resultados no es un error).

### 7) Agregar tests (si aplica)
- Tests de componente para la lógica de UI no trivial.
- Tests de flujo para los recorridos críticos.

### 8) Actualizar la navegación
- Agregar el enlace en el componente de navegación del área privada.
- Verificar permisos: si la página es para un rol específico, respetar el RBAC del módulo
  `identity`.

## Validación
- Los componentes renderizan sin errores y la página responde en su ruta.
- `npm run build` compila sin errores de TypeScript.
- No hay tipos `any`.
- Los Server Components son el caso por defecto y cada `'use client'` tiene motivo.
- Los tipos de la API están regenerados y en uso.
- Los estados de carga, error y vacío están cubiertos.
- Los textos visibles están en español.

## Errores comunes (evitar)
- Usar `'use client'` sin necesidad.
- Poner lógica de negocio en los componentes (va en el backend, o en `lib/` si es de
  presentación).
- Usar tipos `any` o escribir a mano tipos que genera OpenAPI.
- Duplicar primitivas de shadcn/ui dentro de `components/<modulo>/`.
- Dejar textos de UI en inglés.
- No manejar los estados de carga y error.

## Troubleshooting
- Los tipos no coinciden con la API → regenerar con `npm run generate-api-types` (y verificar
  que el backend esté levantado).
- Hace falta estado compartido complejo → revisar si el dato puede resolverse en el Server
  Component antes de introducir estado en el cliente.
- La página queda accesible sin permiso → el gate va en el layout privado y en el endpoint del
  backend, no sólo en la UI.
