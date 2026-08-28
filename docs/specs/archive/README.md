# `docs/specs/archive/` — Specs entregadas

Acá viven las specs de las features que **ya se entregaron**: mergeadas a `main` y desplegadas.

Existe por una razón concreta: sin archivado, `docs/specs/` crece sin límite y en unos meses un
agente que lo lea no puede distinguir lo que está por construirse de lo que ya está en
producción. Termina leyendo la spec de una feature entregada como si fuera el estado deseado.

## Reglas

- **Mueve el Release-Manager**, como último paso de `/ship`, una vez que el PR está mergeado.
  Antes de eso la feature sigue viva y su carpeta se queda en `docs/specs/`.
- **La numeración nunca se reutiliza.** `docs/specs/archive/003-…` significa que el `003` está
  gastado para siempre: la próxima feature toma el número siguiente al mayor entre los dos
  árboles. Reutilizar un número rompe la trazabilidad con las ramas y los PRs.
- **Son historia, no referencia.** Una spec archivada describe lo que se acordó en su momento,
  no cómo funciona el sistema hoy. Para saber cómo funciona hoy:
  - **funcionalmente** → `docs/PROJECT_BRIEF.md` → *Estado de los problemas*, que dice qué
    se resolvió de lo que el cliente pidió y con qué feature;
  - **técnicamente** → `ARCHITECTURE.md`, el código y sus tests.
- **No se editan.** Si algo de una feature entregada cambia, es una feature nueva con su propia
  spec, no un parche sobre la vieja.

## Estructura

Se mueve la carpeta completa, sin tocar su contenido:

```
docs/specs/archive/
└── 001-<short-name>/
    ├── spec.md
    ├── plan.md
    ├── tasks.md
    └── diagrams/
```
