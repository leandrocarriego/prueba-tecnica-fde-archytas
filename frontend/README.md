# Frontend — Plataforma Cordillera

Aplicación Next.js (App Router) con React 19, TypeScript y Tailwind CSS. Es la interfaz de la
Plataforma Cordillera; consume la API de FastAPI que vive en `../backend`.

No hay división `core/` vs `custom/`: es un producto único y el código se organiza **por módulo
de dominio**, igual que el backend.

## Puesta en marcha

```bash
npm install            # instalar dependencias
npm run dev            # servidor de desarrollo (http://localhost:3000)
npm run build          # build de producción
npm start              # servir el build

npm run type-check     # tsc --noEmit
npm run lint           # ESLint
npm run format         # Prettier

npm run generate-api-types   # tipos TS desde el schema de OpenAPI del backend
```

## Variables de entorno

Crear `.env.local` (o copiar `.env.example`):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Sólo las variables con prefijo `NEXT_PUBLIC_` llegan al navegador.

## Estructura

```
frontend/
├── app/
│   ├── (auth)/          rutas públicas: login, reset-password
│   ├── (private)/       rutas protegidas
│   │   ├── layout.tsx   chequeo de autenticación
│   │   ├── page.tsx     dashboard
│   │   └── <modulo>/    una carpeta por módulo de dominio
│   ├── api/             API routes (sesión y proxy hacia el backend)
│   ├── actions/         Server Actions
│   └── layout.tsx       layout raíz
├── components/
│   ├── ui/              primitivas de UI (shadcn/ui, locales)
│   ├── common/          componentes genéricos sin dominio
│   └── <modulo>/        componentes por módulo de dominio
├── lib/                 cliente de API, tipos generados, hooks y utilidades
├── proxy.ts             middleware de sesión
└── public/              estáticos
```

El alias `@/*` apunta a la raíz de `frontend/`.

## Diseño

Las primitivas de `components/ui/` son **shadcn/ui escritas acá**, no un paquete externo: el
proyecto no depende de ningún registry privado y `npm ci` corre sin credenciales.

Los tokens de diseño —colores, radios— viven en `app/globals.css`, en un bloque `@theme` de
Tailwind v4, con modo claro y oscuro. Para cambiar la paleta se tocan esos valores, nunca las
clases repartidas por la app.

## Autenticación

La sesión es una cookie `access_token` httpOnly:

1. `proxy.ts` exige la cookie en toda ruta que no sea pública.
2. `app/(private)/layout.tsx` valida el token contra el backend.
3. Las llamadas del cliente al backend pasan por `/api/proxy/<ruta>`, que inyecta el
   `Authorization: Bearer <token>` desde la cookie.

## Agregar un módulo

1. Página en `app/(private)/<modulo>/page.tsx`.
2. Componentes en `components/<modulo>/`.
3. Tipos y helpers de datos en `lib/<modulo>/`.
4. Mutaciones con Server Actions en `app/actions/`; lecturas desde el cliente por el proxy.

## Estilo de código

- TypeScript estricto, sin `any` (usar `unknown` si hace falta).
- Server Components por defecto; `'use client'` sólo con interactividad, hooks o APIs del navegador.
- Código en inglés (nombres, comentarios); strings de UI en español.
- Componentes en PascalCase, hooks `useAlgo`, rutas en kebab-case.

## Documentación

- `docs/ARCHITECTURE.md` — arquitectura del frontend
- `docs/BEST_PRACTICES.md` — patrones y buenas prácticas
- `../ARCHITECTURE.md` — arquitectura del sistema completo
