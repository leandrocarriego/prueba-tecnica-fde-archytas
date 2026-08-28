# Arquitectura del frontend — Plataforma Cordillera

Aplicación Next.js (App Router) de la Plataforma Cordillera. Para la arquitectura del sistema
completo (backend, módulos de dominio, flujo de datos) ver `../../ARCHITECTURE.md`.

No existe la división `core/` vs `custom/`: es un producto único. El frontend se organiza
**por módulo de dominio**, igual que el backend.

## Principios

1. **Organización por módulo de dominio.** Cada capacidad del negocio tiene su ruta, sus
   componentes y su acceso a datos. Los nombres de los módulos siguen a los del backend
   (`identity`/`auth`, `suppliers`, `catalog`, `purchasing`, `billing`, `sales`, `operations`, …).
2. **Server Components por defecto.** `'use client'` sólo cuando hace falta interactividad,
   hooks o APIs del navegador.
3. **Type safety.** TypeScript estricto, sin `any` (usar `unknown` si hace falta). Los tipos de
   la API se generan desde el schema de OpenAPI (`npm run generate-api-types`).
4. **La sesión vive en una cookie httpOnly.** El token nunca se expone al JavaScript del
   navegador: las llamadas al backend pasan por el proxy del servidor.
5. **Idioma.** El código va en inglés (nombres, comentarios, docstrings); los strings que ve
   el usuario, en español.

## Estructura

```
frontend/
├── app/
│   ├── (auth)/                 # Rutas públicas (el grupo no aparece en la URL)
│   │   ├── layout.tsx          # Marca de agua compartida entre login y reset
│   │   ├── login/
│   │   └── reset-password/
│   ├── (private)/              # Rutas protegidas
│   │   ├── layout.tsx          # Chequeo de autenticación en el servidor
│   │   ├── page.tsx            # Dashboard (/)
│   │   └── <modulo>/           # Una carpeta por módulo de dominio → /<modulo>
│   ├── api/                    # API routes
│   │   ├── auth/               # Sesión: login, logout, me, password/change
│   │   └── proxy/[...path]/    # Proxy autenticado hacia FastAPI
│   ├── actions/                # Server Actions (auth.ts, …)
│   ├── globals.css
│   └── layout.tsx              # Layout raíz (fuente, tema, Toaster)
│
├── components/
│   ├── ui/                     # Primitivas de UI (shadcn/ui, locales)
│   ├── common/                 # Componentes genéricos sin dominio (footer, marca de agua)
│   ├── auth/                   # Componentes del módulo de identidad/autenticación
│   └── <modulo>/               # Componentes por módulo de dominio
│
├── lib/
│   ├── branding.ts             # Configuración de branding de las pantallas de auth
│   ├── utils.ts                # Helpers comunes (`cn`)
│   ├── hooks/                  # Hooks reutilizables (useAuth, useLoading)
│   └── <modulo>/               # Tipos y helpers por módulo (ej. operations/)
│
├── public/                     # Estáticos
├── proxy.ts                    # Middleware: exige cookie de sesión fuera de las rutas públicas
├── next.config.js
├── tailwind.config.ts
└── tsconfig.json
```

Alias de imports: `@/*` apunta a la raíz de `frontend/` (ver `tsconfig.json`).

## Rutas y grupos de rutas

- **`(auth)/`** — rutas públicas. `proxy.ts` las deja pasar sin cookie.
- **`(private)/`** — todo lo que esté acá queda protegido automáticamente por su `layout.tsx`.
  Los grupos entre paréntesis no aparecen en la URL: `app/(private)/suppliers/page.tsx` → `/suppliers`.

## Flujo de autenticación

1. El usuario entra a una ruta protegida.
2. `proxy.ts` (middleware) verifica que exista la cookie `access_token`; si no está, redirige a
   `/login` con el `redirect` original.
3. `app/(private)/layout.tsx` valida el token contra el backend con `getCurrentUser()`.
4. `app/actions/auth.ts` (Server Action) hace login/logout y escribe o borra la cookie httpOnly.

## Acceso al backend

Hay dos caminos, los dos del lado del servidor:

- **Server Actions y route handlers** (`app/actions/`, `app/api/auth/`): llaman a
  `${NEXT_PUBLIC_API_URL}/api/v1/...` y manejan la cookie de sesión.
- **Proxy** (`app/api/proxy/[...path]/route.ts`): las llamadas del cliente van a
  `/api/proxy/<ruta>`; el route handler agrega el header `Authorization: Bearer <token>` leyendo
  la cookie httpOnly y reenvía a `${NEXT_PUBLIC_API_URL}/api/v1/<ruta>`.

Por eso el proxy es un route handler y **no** un `rewrite` de `next.config.js`: un rewrite no
puede inyectar el token de la cookie httpOnly.

`NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) define el destino.

## Agregar un módulo

1. Página: `app/(private)/<modulo>/page.tsx` (Server Component por defecto).
2. Componentes: `components/<modulo>/`.
3. Tipos y helpers de datos: `lib/<modulo>/`.
4. Mutaciones: Server Action en `app/actions/<modulo>.ts`; lecturas desde el cliente,
   por `/api/proxy/...`.

Un módulo nuevo se justifica cuando representa una capacidad del negocio, no cuando
simplemente hay muchos archivos.

## Convenciones de nombres

- Componentes: PascalCase (`JobRunCard.tsx`).
- Hooks: camelCase con prefijo `use` (`useAuth.ts`).
- Utilidades y tipos: camelCase (`taskStateUtils.ts`, `types.ts`).
- Rutas: kebab-case (`reset-password/`).
- Constantes: UPPER_SNAKE_CASE.

## Calidad

```bash
npm run type-check     # tsc --noEmit
npm run lint           # ESLint (next/core-web-vitals)
npm run format:check   # Prettier
```

Ver `BEST_PRACTICES.md` para patrones de componentes, estado, manejo de errores y seguridad.
