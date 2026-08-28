# Skills — Convención e índice

Las skills son **procedimientos operativos y repetibles** que siguen tanto las personas como
los agentes al trabajar sobre la Plataforma Cordillera. Cuando una skill aplica, sus pasos se
siguen en orden y su sección de **Validación** se completa antes de declarar el trabajo hecho
(`AGENTS.md` → "Protocolo de Skills").

Viven acá, **fuera de `.claude/`**, a propósito: un procedimiento del proyecto no le pertenece a
la herramienta con la que se ejecuta. Los archivos de `.claude/commands/` son punteros de una
línea a estas skills, así que integrar otro proveedor de IA es escribir trece punteros en su
formato — no reescribir trece procedimientos. Es la misma razón por la que `AGENTS.md` está en la
raíz y `.claude/CLAUDE.md` sólo lo importa.

**Ninguna skill menciona una herramienta ni una variable suya.** Si una skill dice `$ARGUMENTS`,
está acoplada y hay que corregirla.

## Índice de skills

### La cadena de una feature (SDD)

| Skill | Comando | Para qué |
|---|---|---|
| `specify.md` | `/specify` | Escribir la spec funcional de una feature nueva |
| `clarify.md` | `/clarify` | Resolver las ambigüedades antes de la firma |
| `add_diagrams.md` | `/diagram` | Generar los diagramas Mermaid derivados de la spec |
| `approve_spec.md` | `/approve-spec` | Registrar la firma del cliente (**gate**) |
| `plan.md` | `/plan` | Traducir la spec firmada a un plan técnico, con Constitution Check |
| `tasks.md` | `/tasks` | Desglosar el plan en tareas, cada una mapeada a una skill |
| `analyze.md` | `/analyze` | Verificar la consistencia spec ↔ plan ↔ tasks |
| `implement.md` | `/implement` | Ejecutar las tareas, cada una por su skill |
| `converge.md` | `/converge` | ¿El código es lo que el cliente firmó? |
| `review_feature.md` | `/review-feature` | Quality gate: ¿está bien escrito? (**gate**) |
| `ship_changes.md` | `/ship` | Commit + push + PR contra `main`, y archivar la spec |

### Construir

| Skill | Para qué |
|---|---|
| `add_backend_feature.md` | Agregar una feature dentro de un módulo de `backend/app/modules/`, o crear un módulo nuevo |
| `add_frontend_feature.md` | Agregar una página o capacidad de UI en `frontend/app/(private)/<modulo>/` |
| `add_feature.md` | Feature full-stack: backend + frontend conectados por los tipos de OpenAPI |
| `add_integration.md` | Integrar un sistema externo; la referencia es el portal SIGProv con Playwright |
| `add_celery_task.md` | Agregar trabajo en background con el puente async y garantía de idempotencia |
| `add_database_migration.md` | Crear y aplicar migraciones de Alembic cuando cambian los modelos |
| `add_tests.md` | Escribir tests unitarios, de integración y de extracción contra HTML fijado |

### Operar y mantener

| Skill | Comando | Para qué |
|---|---|---|
| `deploy.md` | — | Preparar y ejecutar un despliegue de producción |
| `debug.md` | — | Encontrar la causa raíz de un fallo y corregirla (transversal, cualquier paso) |
| `project_status.md` | `/status` | Radiografía del estado real del proyecto |
| `inspect_portal.md` | `/portal` | Verificar contra SIGProv la estructura de una sección |
| `add_or_update_skill.md` | — | Crear o actualizar una skill y registrar su trigger |

Cada skill tiene su trigger en el **Mapa de triggers de skills** de `AGENTS.md`. Si una skill
no está en ese mapa, está incompleta.

## Nombres
- Formato: `<verbo>_<objeto>.md`
- `snake_case`, sin prefijos numéricos.
- Ejemplo: `add_backend_feature.md`

## Secciones requeridas (en este orden)
1. Título: `# Skill — <Nombre>`
2. `Tags: [...]` (recomendado)
3. `## Objetivo`
4. `## Cuándo usarla`
5. `## Precondiciones`
6. `## Reglas (ESTRICTO)` *(opcional, si hay restricciones duras)*
7. `## Pasos (ORDEN OBLIGATORIO)`
8. `## Validación`
9. `## Errores comunes (evitar)`
10. `## Troubleshooting`

## Tags sugeridos
`[backend]` `[frontend]` `[feature]` `[modulo]` `[database]` `[celery]` `[integracion]`
`[testing]` `[review]` `[release]` `[deploy]` `[specs]` `[debug]`

## Reglas de estilo
- Las skills se escriben en **español**; el código de los ejemplos, en inglés.
- Los pasos son deterministas y verificables: comandos y rutas explícitas.
- La sección de Validación se escribe con comandos o chequeos concretos, no con adjetivos.
- Evitar lenguaje vago ("debería", "quizás") salvo que no haya alternativa.
- Las rutas y estructuras citadas tienen que existir: monolito modular, módulos en
  `backend/app/modules/<module>/`, frontera entre módulos por eventos (`app/shared/events`).

Para agregar o modificar una skill, seguir `add_or_update_skill.md`.
