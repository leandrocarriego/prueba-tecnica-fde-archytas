# Componentes

Organizados por módulo de dominio, igual que el backend. No hay división `core/` vs `custom/`.

```
components/
├── ui/           # Primitivas de UI (shadcn/ui, locales)
├── common/       # Componentes genéricos que no pertenecen a un dominio
├── auth/         # Componentes de identidad/autenticación
└── <modulo>/     # Un directorio por módulo de dominio
```

## Reglas

- Un componente pertenece al módulo de dominio que representa (`suppliers`, `catalog`,
  `operations`, …). Si es genuinamente transversal, va en `common/`.
- `ui/` es sólo para primitivas reutilizables; no lleva lógica de negocio.
- Server Components por defecto; `'use client'` sólo con interactividad, hooks o APIs del navegador.
- Nombres de archivo en PascalCase para componentes (`JobRunCard.tsx`); las primitivas de
  `ui/` mantienen el kebab-case de shadcn/ui.
- El código va en inglés; los textos que ve el usuario, en español.
