# Skill — Agregar una feature de frontend

Tags: [frontend] [feature] [nextjs]

## Objetivo
Implementar una feature de frontend siguiendo la estructura por módulo de dominio:
- las páginas viven en `frontend/app/(private)/<modulo>/`
- los componentes viven en `frontend/components/<modulo>/`
- las primitivas de UI (shadcn/ui) viven en `frontend/components/ui/`
- **el aspecto no se elige: lo hereda del sistema de diseño** (`docs/design/` +
  `frontend/app/globals.css`)
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
- **Ningún color escrito a mano, ninguna clase de la paleta por defecto de Tailwind** (`UI-01`,
  `UI-02`). Lo verifica un test que rompe el build; no es una recomendación.
- **Una sola acción naranja por pantalla** (`UI-05`). Si parece que hacen falta dos, la pantalla
  está haciendo dos cosas: se escala, no se agrega un segundo botón.

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

### 5) Aplicar el sistema de diseño

**Antes de escribir el markup, abrir `docs/design/`**: la guía de estilos dice qué significa cada
señal y las pantallas de alta fidelidad muestran cómo se compone. Una pantalla nueva no inventa su
lenguaje visual; usa el que ya está acordado con el cliente.

Las reglas completas son `CONVENTIONS.md` → `UI-01` … `UI-10`. Lo que se usa todo el tiempo:

| Necesitás | Usás | Regla |
|---|---|---|
| Un color | un token de `globals.css` (`bg-warn-surface`, `text-danger`, `border-ok-border`) | `UI-01`, `UI-02` |
| Mostrar el estado de un dato | `<Badge tone="ok\|info\|warn\|danger\|draft">` o `.pill*` | `UI-03` |
| Un importe, una fecha, un código | `font-mono` o la clase `.amount` | `UI-04` |
| La acción principal de la pantalla | `<Button variant="brand">`, **una sola** | `UI-05` |
| Una acción secundaria | `variant="outline"`, `"default"` (tinta) o `"ghost"` | `UI-05` |
| Navegar o consultar | `variant="link"` / `text-link` — nunca para guardar o borrar | `UI-06` |
| Avisar que algo quedó afuera | `<Notice>` **arriba** del dato que califica, con su acción | `UI-07` |
| El rótulo de un bloque | `.section-label` | — |

Los cinco significados de color, y ni uno más: **conforme** (verde), **informativo** (azul),
**requiere decisión** (ámbar), **vencido o con error** (rojo) y **sin novedad** (neutro). El
naranja no es un sexto estado: es la acción, y significa "acá tenés que decidir vos".

Si te falta una señal —un estado que ninguna píldora cubre, un color que no existe— **no la
improvises en el componente**: se agrega el token en `globals.css` y su significado en
`docs/design/`, y eso lo decide el `Frontend-Architect`.

---

### 6) Conectar con el backend
- El cliente de API y los helpers de fetch viven en `frontend/lib/`.
- Mutaciones → Server Actions en `frontend/app/actions/`.
- Proxy o lógica de sesión → route handlers en `frontend/app/api/`.
- Nunca llamar al backend con URLs hardcodeadas: usar la configuración de `frontend/lib/`.

### 7) Manejar estados de carga y error
- Estado de carga visible (skeleton o `loading.tsx`).
- Estado de error con mensaje útil **en español**.
- Estado vacío contemplado (lista sin resultados no es un error).

### 8) Agregar tests (si aplica)
- Tests de componente para la lógica de UI no trivial.
- Tests de flujo para los recorridos críticos.

### 9) Actualizar la navegación
- Agregar el enlace en el componente de navegación del área privada, **dentro del grupo del área
  del negocio que le corresponde**.
- Verificar permisos: si la página es para un rol específico, respetar el RBAC del módulo
  `identity`.

## Validación
- Los componentes renderizan sin errores y la página responde en su ruta.
- `npm test` pasa, con `tests/design-system.test.ts` en verde (`UI-01`, `UI-02`).
- La pantalla se comparó contra `docs/design/`: mismos colores, misma tipografía, mismas formas.
- Hay **como mucho un** botón naranja, y es el de la tarea principal.
- Los importes, las fechas y los códigos están en mono tabular.
- Los estados se dibujan con la píldora, no con un `span` propio.
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
- Escribir un color a mano "por esta vez": es lo que hizo que once pantallas dibujaran el mismo
  estado de tres maneras distintas, y es exactamente lo que el test frena.
- Poner el aviso al pie del número que califica. Va **arriba**: primero se dice si se puede confiar
  en el dato, después se muestra.
- No manejar los estados de carga y error.

## Troubleshooting
- Los tipos no coinciden con la API → regenerar con `npm run generate-api-types` (y verificar
  que el backend esté levantado).
- Hace falta estado compartido complejo → revisar si el dato puede resolverse en el Server
  Component antes de introducir estado en el cliente.
- La página queda accesible sin permiso → el gate va en el layout privado y en el endpoint del
  backend, no sólo en la UI.
